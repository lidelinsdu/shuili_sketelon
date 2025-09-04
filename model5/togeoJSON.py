import geopandas as gpd
import numpy as np
import rasterio
import yaml
from rasterio.features import shapes
import utils.file_path_processor

with open("config/configuration_local.yaml", 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)['model5']

tif_temp_dir = config['tif-temp-dir']  # 重分类后临时tif文件存放路径


# ========================
# 参数设置
# ========================


def generate_geoJSON(input_tif_path, out_geojson_path):
    output_geojson = out_geojson_path
    input_tif = input_tif_path
    classes = [
        (0.6, 1.0, 2, "湿润"),
        (0.5, 0.6, 3, "轻度干旱"),
        (0.4, 0.5, 4, "中度干旱"),
        (0.3, 0.4, 5, "严重干旱"),
        (0.00, 0.3, 5, "特大干旱")  # 注意：<0.25
    ]

    # 1. 读取TIFF文件
    with rasterio.open(input_tif) as src:
        # 读取第一个波段（假设是单波段）
        band = src.read(1).astype(np.float32)

        # 获取NoData值
        nodata = src.nodata
        if nodata is not None:
            band[band == nodata] = np.nan

        # 创建重分类后的数组
        classified = np.full(band.shape, np.nan)  # 初始化为NaN

        # 2. 重分类：将连续值映射到等级
        for min_val, max_val, code, name in classes:
            if min_val == 0.0:
                # 重旱: < 0.25
                mask = (band < max_val)
            else:
                # 其他区间: [min_val, max_val)
                mask = (band >= min_val) & (band < max_val)
            classified[mask] = code

        # 设置仿射变换（用于坐标转换）
        transform = src.transform
        crs = src.crs

    # 3. 矢量化：将栅格转为多边形
    results = (
        {'properties': {'DN': v}, 'geometry': s}
        for s, v in shapes(classified.astype(np.float32), mask=np.isfinite(classified), transform=transform)
    )

    # 4. 转换为GeoJSON格式
    features = list(results)
    for feature in features:
        feature['properties']['DN'] = int(feature['properties']['DN'])  # 转为整数

    # 5. 创建GeoDataFrame
    gdf = gpd.GeoDataFrame.from_features(features, crs=crs)

    # 6. （可选）添加级别名称字段
    level_map = {2: "湿润", 3: "轻旱", 4: "中旱", 5: "重旱"}
    gdf['level_name'] = gdf['DN'].map(level_map)

    # 7. 保存为GeoJSON
    gdf.to_file(output_geojson, driver='GeoJSON', encoding='utf-8')
    return True
