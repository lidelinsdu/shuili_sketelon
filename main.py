import time
import json
import datetime as dt

import uvicorn
from fastapi import FastAPI

from model1.hefeng_weather_predict import request_weather
# 来水预报
from model1.inflow_ARIMA import arima_path
from model1.inflow_SARIMA import sarima_path
from model1.inflow_SARIMAX import sarimax_path
from model2.main import request_E
from model5.algorithm import nir_red_to_smi, plot_heatmap

app = FastAPI()


@app.get('/')
def hello():
    return '欢迎来到我的fastAPI应用！'


@app.get('/inflow_predict')
def inflow_predict(file_path: str, predict_days: int, modelname='arima'):
    """
    来水预报
    :param file_path: 文件路径
    :param predict_days: 预测天数
    :param modelname: 可选预测模型【"arima", "sarima", "sarimax"】
    :return: 未来predict_days天的预测来水以及未来30天的降水预报
    """
    start_time = time.perf_counter()  # 记录函数开始时间
    print(file_path)
    predict_days = int(predict_days)
    try:
        if modelname == 'arima':
            result = arima_path(file_path, predict_days)  # 调用 arima_path 函数处理数据
        elif modelname == 'sarimax':
            result = sarimax_path(file_path, predict_days)  # 调用 sarimax_path 函数处理数据
        elif modelname == 'sarima':
            result = sarima_path(file_path, predict_days)  # 调用 sarima_path 函数处理数据
        else:
            return {'error': 'Invalid model name'}

        end_time = time.perf_counter()  # 记录函数结束时间
        execution_time = end_time - start_time  # 计算函数执行时间（单位：秒）
        precip_list = request_weather()
        result['precipitation'] = precip_list
        result['execution_time'] = execution_time * 1000  # 添加执行时间字段（单位：毫秒）
        return result
    except Exception as e:
        return {'error': str(e)}


@app.get('/water_predict')
def water_predict(plant_d, begin_d, end_d, kind):
    """
    需水预测
    :param plant_d: 种植日期
    :param begin_d: 开始日期
    :param end_d: 结束日期
    :param kind: 作物类型，枚举
    :return: 给出单株植物每日需水序列以及总需水量
    """
    ed = dt.datetime.strptime(end_d, "%Y-%m-%d")
    td = dt.datetime.today()
    lap = (td - ed).days
    if lap <= 30:
        return request_E(plant_d, begin_d, end_d, kind)
    else:
        return "<UNK>30<UNK>"


@app.get('/water_allocation')
def water_allocation():
    return "hello world"


@app.get('/water_dispatch')
def water_dispatch():
    return "hello world"


@app.get('/flood_drought_defend/get_smi')
def flood_drought_defend_get_smi(red_tif_dir, nir_tif_dir):
    """
    获取对应遥感图像的土壤含水量数组，分辨率与文件相同
    :param red_tif_dir: 红波tif路径
    :param nir_tif_dir: 近红外tif路径
    :return: 土壤含水量二维数组
    """
    smi = nir_red_to_smi(red_tif_dir, nir_tif_dir)
    return

@app.get('/flood_drought_defend/draw_heatmap')
def draw_heatmap(smi_2d_data):
    """
    绘制热度图
    :param smi_2d_data: 土壤含水量数组
    :return: 热度图
    """
    plot_heatmap(smi_2d_data)
    return "file_name"


if __name__ == '__main__':
    uvicorn.run(app, port=8081)
