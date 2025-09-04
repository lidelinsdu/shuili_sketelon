import datetime as dt
import json
import math
import os.path
import zipfile
import utils.file_path_processor

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

from model5.togeoJSON import generate_geoJSON
from utils.hefeng_weather_predict import request_weather

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams.update({'font.size': 10})  # 设置字体大小

from PIL import Image
from osgeo import gdal
from scipy.stats import linregress
import seaborn as sns

MINUS_RATE = 1.08
HEATMAP_DIR = "model5/heatmap/"
with open("config/configuration_local.yaml", 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)['model5']


def create_example(is_write=False):
    data = []
    for i in range(100):
        list = []
        for j in range(100):
            list.append(5)
        data.append(list)
    if is_write:
        with open('example.json', 'w', encoding='utf-8') as f:
            obj = {
                "humidity": data
            }
            json.dump(obj, f, indent=4, ensure_ascii=False)
    return data


def print_data(data):
    l = len(data)
    for i in range(l):
        print(data[i])
    print('-------------------------------------------------------------')


def init(data):
    humidity = data["humidity"]  # 100*100
    true_h = data["true_points"]  # list[obj]
    adjusted_data = adjust(humidity, true_h)

    return adjusted_data


def adjust(data, true_points):
    diff_num = len(true_points)
    sum = 0
    for i in true_points:
        x = i['x']
        y = i['y']
        humidity = i['true_humidity']
        sum += humidity
        sum -= data[x][y]
    ave = sum / diff_num
    # for i in range(len(data)):
    #     for j in range(len(data[0])):
    #         data[i][j] -=ave
    array = np.array(data)
    array = array - ave
    for i in true_points:
        x = i['x']
        y = i['y']
        humidity = i['true_humidity']
        array[x][y] = humidity
    return array


def predict(data, days):
    array = np.array(data)
    array = array - days * MINUS_RATE
    for i in range(len(array)):
        for j in range(len(array[i])):
            if array[i][j] < 0:
                array[i][j] = 0
    return array


def extract_soil_line(red_band, nir_band, num_bins=256):
    """
    输入：
        red_path: 红光波段文件路径 (GeoTIFF)
        nir_path: 近红外波段文件路径 (GeoTIFF)
        num_bins: 分组数量，默认为256
    输出：
        a, b: 拟合出的土壤线方程参数：NIR = a * Red + b
    """

    # 展平为一维数组，并过滤无效值
    valid_mask = (red_band > 0) & (nir_band > 0)
    red_flat = red_band[valid_mask]
    nir_flat = nir_band[valid_mask]

    # Step 3: 按 Red 分组，每组取 NIR 最小值作为初始土壤点
    red_min, red_max = np.min(red_flat), np.max(red_flat)
    bin_edges = np.linspace(red_min, red_max, num_bins + 1)

    soil_points_x = []
    soil_points_y = []

    for i in range(num_bins):
        in_bin = (red_flat >= bin_edges[i]) & (red_flat < bin_edges[i + 1])
        if np.any(in_bin):
            min_nir_idx = np.argmin(nir_flat[in_bin])
            soil_points_x.append(red_flat[in_bin][min_nir_idx])
            soil_points_y.append(nir_flat[in_bin][min_nir_idx])

    soil_points_x = np.array(soil_points_x)
    soil_points_y = np.array(soil_points_y)

    # Step 4: 分割子集并计算相关系数，选择最优子集
    n = len(soil_points_x)
    indices = np.argsort(soil_points_x)
    sorted_x = soil_points_x[indices]
    sorted_y = soil_points_y[indices]

    subsets = [
        (0, int(0.75 * n)),  # 0% ~ 75%
        (int(0.25 * n), n),  # 25% ~ 100%
        (int(0.25 * n), int(0.75 * n))  # 25% ~ 75%
    ]

    best_corr = -np.inf
    best_subset = None

    for start, end in subsets:
        x_sub = sorted_x[start:end]
        y_sub = sorted_y[start:end]
        if len(x_sub) < 2:
            continue
        slope, intercept, r_value, p_value, std_err = linregress(x_sub, y_sub)
        if r_value ** 2 > best_corr:
            best_corr = r_value ** 2
            best_subset = (x_sub, y_sub)

    x_eff, y_eff = best_subset

    # Step 5: 迭代剔除垂直偏差最大的点
    max_iter = 100
    threshold = 0.95  # 相关系数阈值，也可自定义迭代次数
    current_x, current_y = x_eff.copy(), y_eff.copy()

    for _ in range(max_iter):
        slope, intercept, _, _, _ = linregress(current_x, current_y)
        pred_y = slope * current_x + intercept
        residuals = np.abs(pred_y - current_y)
        max_res_idx = np.argmax(residuals)
        current_x = np.delete(current_x, max_res_idx)
        current_y = np.delete(current_y, max_res_idx)
        if len(current_x) < 2:
            break
        slope_new, intercept_new, r_new, _, _ = linregress(current_x, current_y)
        if r_new ** 2 < threshold:
            break

    final_x, final_y = current_x, current_y

    # Step 6: 最终拟合土壤线
    slope_final, intercept_final, r_final, _, _ = linregress(final_x, final_y)
    print(f"最终拟合土壤线方程：NIR = {slope_final:.4f} * Red + {intercept_final:.4f}")
    print(f"相关系数 R² = {r_final ** 2:.4f}")

    # # 可视化最终结果
    # x_plot = np.array([red_min, red_max])
    # y_plot = slope_final * x_plot + intercept_final
    #
    # plt.plot(x_plot, y_plot, 'r-', linewidth=2, label=f'Soil Line\nNIR={slope_final:.2f}*Red+{intercept_final:.4f}')
    # plt.scatter(final_x, final_y, s=20, color='green', label='Final Soil Points')
    # plt.xlabel('Red Reflectance')
    # plt.ylabel('NIR Reflectance')
    # plt.title('Soil Line Extraction in NIR-Red Feature Space')
    # plt.legend()
    # plt.grid(True)
    # plt.show()

    return slope_final, intercept_final


def nir_red_to_smi(red_band_file, nir_band_file):
    """
    利用红波和近红外波对土壤含水量反射率变化率的不同计算土壤含水量
    :param red_band_file: 红波tif文件路径
    :param nir_band_file: 近红外波tif文件路径
    :return: 计算完土壤含水量的二维数组
    """
    height, width = Image.open(nir_band_file).size
    # 加载 Red 和 NIR 波段
    red_file = gdal.Open(red_band_file)
    red_band = red_file.GetRasterBand(1)
    red = red_band.ReadAsArray().astype(float) * 10e-4
    nir_file = gdal.Open(nir_band_file)
    nir_band = nir_file.GetRasterBand(1)
    nir = nir_band.ReadAsArray().astype(float) * 10e-4
    example = gdal.Open(red_band_file, gdal.GA_ReadOnly)
    width = example.RasterXSize
    height = example.RasterYSize
    bands = example.RasterCount

    geotransform = example.GetGeoTransform()
    projection = example.GetProjection()

    data_info = {
        'height': height,
        'width': width,
        'bands': bands,
        'geotransform': geotransform,
        'projection': projection,
    }

    # 掩膜处理：去除无效值（如云、水体）
    mask = (red > 0) & (nir > 0)
    red_masked = red[mask]
    nir_masked = nir[mask]

    # 绘制散点图
    # plt.scatter(red_masked, nir_masked, s=1, c='gray', alpha=0.5)

    # 土壤线
    x = np.linspace(0, 0.5, 400)
    k, b = extract_soil_line(red, nir)
    # plt.plot(x, x * k + b, 'r-', label='soil Edge')
    print(f'土壤线：NIR={k:.2f}RED+{b:.4f}')

    smi = np.zeros_like(red)
    # for i in range(width):
    #     for j in range(height):
    #         smi[i, j] = smmrs(red_masked[i * width + j], nir_masked[i * width + j], k)
    smi = smmrs(red, nir, k)
    # plt.scatter(red_masked, smi, c='red', alpha=0.5)
    return smi, data_info


def smmrs(red, nir, m, ):
    """
    SMMRS值与土壤的含水量之间的相关系数 > 0.8
    :param red: 红波反射率  0~1
    :param nir: 近红外波反射率  0~1
    :param m:  土壤线斜率
    :return: smmrs值
    """
    a = 1 / math.sqrt(m ** 2 + 1)
    res = np.round(1 - a * (red + m * nir), 2)
    return np.clip(res, 0, 1)


def normalized(data):
    data = np.array(data, dtype=float)
    valid_data = data[~np.isnan(data)]

    # 检查是否有足够数据
    if len(valid_data) == 0:
        raise ValueError("数组中没有有效数据（全为 NaN）")
    elif len(valid_data) == 1:
        # 只有一个有效值，归一化为 0.0
        normalized = np.full(data.shape, np.nan)
        normalized[~np.isnan(data)] = 0.0
    else:
        # 步骤 2: 计算全局 min 和 max（忽略 NaN）
        global_min = valid_data.min()
        global_max = valid_data.max()

        # 防止除以零（所有值相等）
        if global_max == global_min:
            normalized = np.full(data.shape, np.nan)
            normalized[~np.isnan(data)] = 0.0
        else:
            # 步骤 3: 归一化所有非 NaN 元素
            normalized = np.full(data.shape, np.nan)
            normalized[~np.isnan(data)] = (data[~np.isnan(data)] - global_min) / (global_max - global_min)

    return normalized


def plot_heatmap(smi_2d, filename="test"):
    """
    绘制土壤含水量热度图
    :param filename: 希望保存的文件名
    :param smi_2d: 土壤含水量2d数组
    :return: 文件路径
    """
    plt.figure()

    # 使用 seaborn 的 heatmap 函数进行绘图
    sns.heatmap(smi_2d, annot=False, cmap='viridis', cbar=True)

    plt.title(f"{filename}含水量分布图")
    plt.tight_layout()
    filename = f"../{HEATMAP_DIR}{filename}.png"
    plt.savefig(filename)
    # plt.show()
    return filename


def get_dynamic_smi(file_list):
    """

    :param file_list:
    :return: 存放geojson文件夹路径
    """
    geojson_save_dir = config['geojson-save-dir']

    folder_name = dt.datetime.now().strftime("%Y%m%d%H%M%S")  # 存放到这个文件夹
    os.makedirs(os.path.join(geojson_save_dir, folder_name), exist_ok=True)
    for i in file_list:
        red_file = i["red_dir"]
        nir_file = i["nir_dir"]
        smi, data_info = nir_red_to_smi(red_file, nir_file)

        tiff_path = get_file_name(red_file)
        write_tiff_file(smi, data_info, tiff_path)  # 写入

        output_geojson_path = geojson_save_dir + folder_name + '/' + tiff_path.split('/')[-1].replace('.tif',
                                                                                                      '.geojson')
        success = generate_geoJSON(tiff_path, output_geojson_path)
    return geojson_save_dir + folder_name


def get_continuous_dry_day() -> dict:
    day_list = request_weather()['daily']
    no_rain_day = []
    for i in day_list:
        if i["precip"] == "0" or i["precip"] == "0.0" or float(i["precip"]) == 0.0:
            no_rain_day.append(i["fxDate"])
            continue
        else:
            break
    return {
        "count": len(no_rain_day),
        "no_rain_day_list": no_rain_day,
    }


def get_rain_avg_lap_rate(span: str, present_inflow: float, date: dt.datetime, history_file_name: str = None):
    present_inflow = float(present_inflow)
    year = date.year
    month = date.month
    with open("config/configuration_local.yaml", 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)['model5']
    data_dir = config['history-data-dir']
    if history_file_name is None:
        history_file_name = data_dir
    with open(history_file_name, 'r', encoding='utf-8') as f:
        df = pd.read_csv(f)
    if span == "year":
        rows = df[df["DATE"].map(
            lambda x: dt.datetime.strptime(x, "%Y/%m/%d") < dt.datetime(year - 1, date.month, date.day)
        )]
        all_precip_list = list(rows["PRCP"])
        valid_precip_list = [i * 25.4 if abs(i - 99.99) > 0.1 else 0 for i in all_precip_list]
        all_precip = round(sum(valid_precip_list), 1)

    elif span == "month":
        rows = df[df["DATE"].map(
            lambda x: dt.datetime.strptime(x, "%Y/%m/%d") < dt.datetime(year - 1, month, date.day)
                      and dt.datetime.strptime(x, "%Y/%m/%d").month == date.month
        )]
        all_precip_list = list(rows["PRCP"])
        valid_precip_list = [i * 25.4 if abs(i - 99.99) > 0.1 else 0 for i in all_precip_list]
        all_precip = round(sum(valid_precip_list), 1)
    else:
        # 先计算处于哪一旬
        day = date.day
        flag = 1
        if 1 <= day < 11:
            flag = 0
        elif 11 <= day < 21:
            flag = 1
        else:
            flag = 2
        if flag != 2:
            rows = df[df["DATE"].map(
                lambda x: dt.datetime(year - 1, month, 10 * flag + 1) <=
                          dt.datetime.strptime(x, "%Y/%m/%d") <
                          dt.datetime(year - 1, month, (flag + 1) * 10 + 1))]
        else:
            rows = df[df["DATE"].map(
                lambda x: dt.datetime.strptime(x, "%Y/%m/%d") >= dt.datetime(year - 1, month, 21)
            )]
        all_precip_list = list(rows["PRCP"])
        valid_precip_list = [i * 25.4 if abs(i - 999.9) > 0.1 else 0 for i in all_precip_list]
        all_precip = round(sum(valid_precip_list), 1)

    rate = round((present_inflow - all_precip) / all_precip, 3)
    if rate < 0:
        res = f"相比去年同比下降{round(abs(rate) * 100, 1)} %"
    else:
        res = f"相比去年同比上升{round(abs(rate) * 100, 1)} %"

    return res


def write_tiff_file(smi_list, data_info, filename):
    width = data_info['width']
    height = data_info['height']
    geotransform = data_info['geotransform']
    projection = data_info['projection']

    driver = gdal.GetDriverByName('GTiff')
    dataset = driver.Create(filename, width, height, 1, gdal.GDT_Float32)

    band = dataset.GetRasterBand(1)
    dataset.SetGeoTransform(geotransform)
    dataset.SetProjection(projection)
    band.WriteArray(smi_list)
    dataset.FlushCache()
    dataset = None
    return filename


def read_my_tiff(file_dir):
    file = gdal.Open(file_dir, gdal.GA_ReadOnly)
    band = file.GetRasterBand(1)
    array = band.ReadAsArray()
    print(array.shape)


def get_file_name(file_dir):
    filename = file_dir.split("/")[-1]
    filename_part = filename.split("_")
    filename = filename_part[0] + 'smi.tif'
    with open("config/configuration_local.yaml", 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)['model5']
    if not os.path.exists(config['smi-save-dir']):
        os.makedirs(config['smi-save-dir'])
    full_path = config['smi-save-dir'] + filename
    return full_path


def zipDir(dirpath, outFullName):
    """
    压缩指定文件夹
    :param dirpath: 目标文件夹路径
    :param outFullName: 压缩文件保存路径+xxxx.zip
    :return: 无
    """
    zip = zipfile.ZipFile(outFullName, "w", zipfile.ZIP_DEFLATED)
    for path, dirnames, filenames in os.walk(dirpath):
        # 去掉目标根路径，只对目标文件夹下的文件及文件夹进行压缩
        fpath = path.replace(dirpath, '')
        for filename in filenames:
            zip.write(os.path.join(path, filename), os.path.join(fpath, filename))
    zip.close()


def set_min_area(file_path):
    data = gpd.read_file(file_path)
    data = data.to_crs(epsg=4326)
    data['area'] = data.geometry.area
    min_area = 100
    filtered_data = data[data['area'] >= min_area]
    filtered_data.to_file('filtered_data.geojson', driver='GeoJSON')


if __name__ == '__main__':
    set_min_area('./geojson/resultsmi.geojson')
