import json
import math

import matplotlib.pyplot as plt
import numpy as np

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
    red = gdal.Open(red_band_file).ReadAsArray().astype(float) * 10e-6
    nir = gdal.Open(nir_band_file).ReadAsArray().astype(float) * 10e-6

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

    # L = (-1 / k) * x
    # plt.plot(x, L, 'b-', label='L Edge')
    # 拟合干边（最大值包络线）
    # red_unique = np.unique(red_masked)
    # nir_dry = [np.percentile(nir_masked[abs(red_masked - r) < 0.01], 95) for r in red_unique]
    # dry_coeff = np.polyfit(red_unique, nir_dry, deg=1)
    # dry_line = np.poly1d(dry_coeff)
    # # plt.plot(red_unique, dry_line(red_unique), 'r-', label='Dry Edge')
    #
    # # 拟合湿边（最小值包络线）
    # nir_wet = [np.percentile(nir_masked[abs(red_masked - r) < 0.01], 5) for r in red_unique]
    # wet_coeff = np.polyfit(red_unique, nir_wet, deg=1)
    # wet_line = np.poly1d(wet_coeff)
    # plt.plot(red_unique, wet_line(red_unique), 'b-', label='Wet Edge')

    # plt.xlabel('Red Reflectance')
    # plt.ylabel('NIR Reflectance')
    # plt.legend()
    # plt.title('NIR-Red Feature Space with Dry/Wet Edges')
    # plt.show()

    smi = np.zeros_like(red)
    # for i in range(width):
    #     for j in range(height):
    #         smi[i, j] = smmrs(red_masked[i * width + j], nir_masked[i * width + j], k)
    smi = smmrs(red, nir, k)
    # plt.scatter(red_masked, smi, c='red', alpha=0.5)
    return smi


def smmrs(red, nir, m, ):
    """
    SMMRS值与土壤的含水量之间的相关系数 > 0.8
    :param red: 红波反射率  0~1
    :param nir: 近红外波反射率  0~1
    :param m:  土壤线斜率
    :return: smmrs值
    """
    a = 1 / math.sqrt(m ** 2 + 1)
    return 1 - a * (red + m * nir)


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
    filename = f"{HEATMAP_DIR}{filename}.png"
    # with open(filename, "wb") as f:
    plt.savefig(filename)
    # plt.show()
    return filename


def get_dynamic_smi(file_list):
    smi_list = []
    for i in file_list:
        red_file = i["red_dir"]
        nir_file = i["nir_dir"]
        smi = nir_red_to_smi(red_file, nir_file)
        smi_list.append(smi)
    return smi_list


def get_continuous_dry_day() -> dict:
    day_list = request_weather()
    no_rain_day = []
    for i in day_list:
        if i["precip"] == "0" or i["precip"] == "0.0" or float(i["precip"]) == 0.0:
            no_rain_day.append(i["date"])
            continue
        else:
            break
    return {
        "count": len(no_rain_day),
        "no_rain_day_list": no_rain_day,
    }


def get_rain_avg_lap_rate(span: str, history_avg, precip_list, ):
    precip_sum = 0
    for precip in precip_list:
        precip_sum += precip["precip"]

    day_count = len(precip_list)
    history_sum = day_count * history_avg
    rate = (precip_sum - history_sum) / history_sum
    return f"{rate:.4f}"


if __name__ == '__main__':
    red_file_dir = "tifs/DJI_20230215104141_0058_MS_R.TIF"
    nir_file_dir = "tifs/DJI_20230215104143_0059_MS_NIR.TIF"
    smi = nir_red_to_smi(red_file_dir, nir_file_dir)
    plot_heatmap(smi, )
