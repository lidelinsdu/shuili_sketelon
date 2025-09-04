import geopandas as gpd
import numpy as np
from affine import Affine
from rasterio.features import rasterize, shapes
from shapely.geometry import shape
from skimage import morphology

# -------------------------------
# 1. 参数设置
# -------------------------------
input_geojson = "../model5/geojson/resultsmi.geojson"      # 输入 GeoJSON
output_geojson = "cleaned_fast.geojson"  # 输出
pixel_size = 1.0                     # 栅格分辨率（单位：米）
min_area_m2 = 10             # 最小保留面积（平方米）
connectivity = 4                    # 连通性：1=四邻域，2=八邻域
fill_holes = False                   # 是否填充内部孔洞

# -------------------------------
# 2. 读取 GeoJSON
# -------------------------------
gdf = gpd.read_file(input_geojson)

if gdf.empty:
    raise ValueError("GeoJSON 为空")

# 确保是等面积投影（用于面积计算）
original_crs = gdf.crs
gdf = gdf.to_crs("EPSG:3857")  # Web Mercator（近似等面积，适合小范围）

# 获取全局边界
bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
width = int(np.ceil((bounds[2] - bounds[0]) / pixel_size))
height = int(np.ceil((bounds[1] - bounds[3]) / pixel_size)) * (-1)

# 构建仿射变换矩阵（地理坐标 → 像素坐标）
transform = Affine.translation(bounds[0], bounds[3]) * Affine.scale(pixel_size, -pixel_size)

print(f"栅格尺寸: {width} x {height}, 分辨率: {pixel_size}m")

# -------------------------------
# 3. 矢量 → 栅格（烧录为二值图像）
# -------------------------------
# 创建全0数组
raster = np.zeros((height, width), dtype=np.uint8)

# 将所有多边形烧录为 1
# 注意：rasterize 需要 (geometry, value) 对
features = [(geom, 1) for geom in gdf.geometry if geom is not None and not geom.is_empty]

raster = rasterize(
    shapes=features,
    out=raster,
    transform=transform,
    fill=0,
    dtype=np.uint8
)

print(f"栅格化完成，非零像素数: {np.sum(raster)}")

# -------------------------------
# 4. 去除小碎片（核心步骤）
# -------------------------------
# 方法1：直接去除小连通区域
cleaned = morphology.remove_small_objects(
    raster.astype(bool),           # 转为布尔
    min_size=int(min_area_m2 / (pixel_size ** 2)),  # 最小面积换算为像素数
    connectivity=connectivity
)

# 可选：去除小孔洞（内部空洞）
if fill_holes:
    cleaned = ~morphology.remove_small_holes(
        ~cleaned,
        area_threshold=int(min_area_m2 / (pixel_size ** 2)),
        connectivity=connectivity
    )

# 转回 uint8
cleaned = cleaned.astype(np.uint8)

print("小碎片已去除")

# -------------------------------
# 5. 栅格 → 矢量（多边形化）
# -------------------------------
# 使用 rasterio 提取轮廓
results = list(shapes(cleaned, mask=cleaned == 1, transform=transform, connectivity=connectivity))

# 转为几何对象
polygons = []
for geom_json, value in results:
    if value == 1:
        geom = shape(geom_json)
        if geom.is_valid and geom.area > 0:
            # 可选：简化几何（减少顶点）
            # geom = geom.simplify(tolerance=0.5)
            polygons.append(geom)

# -------------------------------
# 6. 构建 GeoDataFrame 并保存
# -------------------------------
if not polygons:
    print("警告：没有保留任何面")
    result_gdf = gpd.GeoDataFrame(geometry=[], crs="EPSG:3857")
else:
    result_gdf = gpd.GeoDataFrame([{'geometry': poly} for poly in polygons], crs="EPSG:3857")

# 转回原始坐标系
result_gdf = result_gdf.to_crs(original_crs)

# 保存
result_gdf.to_file(output_geojson, driver="GeoJSON")

print(f"✅ 处理完成！共 {len(result_gdf)} 个多边形，已保存至 {output_geojson}")