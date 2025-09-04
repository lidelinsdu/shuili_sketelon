import json
from collections import defaultdict

import numpy as np
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

# 读取tif
with rasterio.open('../model5/smi_tifs/resultsmi.tif') as src:
    data = src.read(1)  # 假设单波段
    transform = src.transform
    crs = src.crs

# 分类为四个等级
bins = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
# 替代原来的 digitize 方法
labels = np.full(data.shape, -1, dtype=np.int8)  # 默认 -1 表示无效

# 正确划分区间，包含 1.0
labels[(data >= 0.0) & (data < 0.25)] = 0
labels[(data >= 0.25) & (data < 0.5)] = 1
labels[(data >= 0.5) & (data < 0.75)] = 2
labels[(data >= 0.75) & (data <= 1.0)] = 3  # 包含 1.0
# 注意：nan 或 masked 数据要处理
labels = np.nan_to_num(labels, nan=-1).astype(int)  # -1 表示无效值

from skimage import filters, morphology

selem = morphology.disk(2)  # 半径2像素的圆形结构（约5x5）
filtered_labels = filters.rank.modal(labels, selem)

mask = (filtered_labels >= 0)  # 排除无效值
results = (
    {'properties': {'value': v}, 'geometry': s}
    for s, v in shapes(filtered_labels.astype(np.int16), mask=mask, transform=transform)
)

gjson = {
    "type": "FeatureCollection",
    "features": []
}

# 按 value 分组
collections = defaultdict(list)

for feat in results:
    val = int(feat['properties']['value'])
    collections[val].append(shape(feat['geometry']))

# 合并每个类别的所有多边形
final_features = []
level_names = {0: "重度干旱", 1: "干旱", 2: "轻度干旱", 3: "湿润"}

for val, geoms in collections.items():
    if not geoms:
        continue
    # 使用 unary_union 合并同类多边形
    merged = unary_union(geoms)
    # 可能是 MultiPolygon 或 Polygon
    if merged.geom_type == 'Polygon':
        geom_json = mapping(merged)
    else:
        geom_json = mapping(merged)

    final_features.append({
        "type": "Feature",
        "properties": {
            "class": level_names[val],
            "value": val
        },
        "geometry": geom_json
    })

gjson["features"] = final_features

with open('output.geojson', 'w', encoding='utf-8') as f:
    json.dump(gjson, f, ensure_ascii=False, indent=2)