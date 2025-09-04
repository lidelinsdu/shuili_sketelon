import datetime as dt
import json
import os
import time
from datetime import datetime
from typing import Optional

import pandas as pd
import yaml
from fastapi import APIRouter, UploadFile, File

import utils
from model1.inflow_ARIMA import arima_path
from model1.inflow_SARIMA import sarima_path
from model1.inflow_SARIMAX import sarimax_path
from model1.sarima_predict import sarima_predict
from model1.utils.construct_data_from_history import sum_monthly_series
from model3.implement import sum_data_to_10days
from utils.hefeng_weather_predict import request_weather
import utils.file_path_processor
router_1 = APIRouter(
    prefix="/model1",
    tags=["来水预报模型"]
)


@router_1.get('/inflow_predict')
def inflow_predict(file_path, predict_steps: Optional[int] = 12,
                   predict_begin_date: str = None):
    """
    来水预报
    \n:param predict_begin_date: 可选 预测开始日期 %Y-%m-%d， 默认为当月一号, 尽量选当月第一天，若输入不为当月一号则采用默认
    \n:param file_path: csv文件路径, 文件包括两列，['inflow', 'time']分别代表[来水量， 时间戳（天）]
    \n:param predict_steps: 预测步数 int， 默认=12
    \n:return: 从predict_begin_date开始的未来predict_days天的预测来水以及从当天开始的未来30天的降水预报
    """
    with open("config/configuration_local.yaml", 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)['model1']
    modelname = config['default-method']
    start_time = time.perf_counter()  # 记录函数开始时间
    df = pd.read_csv(file_path)
    last_row = df.iloc[-1]
    last_date = last_row['time']  # 预测数据最后一天
    last_date = datetime.strptime(last_date, '%Y-%m-%d')
    if predict_begin_date is None:
        predict_begin_date = dt.datetime.now()
    else:
        predict_begin_date = dt.datetime.strptime(predict_begin_date, '%Y-%m-%d')
    if predict_begin_date.day != 1:
        predict_begin_date = predict_begin_date.replace(day=1)
    invalid_steps = -1 + 12 * (predict_begin_date.year - last_date.year) + predict_begin_date.month - last_date.month
    steps = predict_steps + invalid_steps
    # 读取历史数据中最后一天的信息
    # 计算gap， gap = (predict_begin_date - last_date).days
    # 预测长度为gap + predict_days
    # res = res[-predict_days:]

    try:
        if modelname == 'arima':
            result = arima_path(file_path, steps)  # 调用 arima_path 函数处理数据
        elif modelname == 'sarimax':
            result = sarimax_path(file_path, steps)  # 调用 sarimax_path 函数处理数据
        elif modelname == 'sarima':
            result = sarima_path(file_path, steps)  # 调用 sarima_path 函数处理数据
        else:
            return {'error': 'Invalid model name'}

        end_time = time.perf_counter()  # 记录函数结束时间
        execution_time = end_time - start_time  # 计算函数执行时间（单位：秒）
        precip_list = [{"date": i["fxDate"], "precip": i["precip"]} for i in request_weather()["daily"]]
        result['precipitation'] = precip_list
        result['execution_time'] = execution_time * 1000  # 添加执行时间字段（单位：毫秒）

        predict_list = result['forecast_inflow'][invalid_steps:]  # 截取有效部分
        result_list = []  # 有效结果列表 其中date为当月的一号， predict_precip是预测当月的来水量
        for i in range(predict_steps):
            date_str = predict_begin_date.strftime('%Y-%m-%d')
            result_list.append({
                "date": date_str,
                "predict_precip": predict_list[i],
            })
            predict_begin_date = predict_begin_date.replace(month=predict_begin_date.month % 12 + 1)
            if predict_begin_date.month == 1:  # 下一个月为1了， 下一年
                predict_begin_date = predict_begin_date.replace(year=predict_begin_date.year + 1)

        # 以下计算当月每一天的来水量
        predict_precip_daily_list = cal_predict_precip_daily(result_list)
        result['forecast_inflow'] = predict_precip_daily_list
        return result
    except Exception as e:
        return {'error': str(e)}


def cal_predict_precip_daily(data_list):
    """计算逐日来水量"""
    result = []
    months = len(data_list)
    with open("config/configuration_local.yaml", 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)['model1']
    with open(config['data-dir'], 'r', encoding="utf-8") as f:
        rate_list_json = json.load(f)
    df = pd.DataFrame(rate_list_json)
    for i in data_list:
        precip = i["predict_precip"]
        day_i = dt.datetime.strptime(i["date"], '%Y-%m-%d').date()
        month_i = day_i.month
        while day_i.month == month_i:
            row_i = df[df["date"] == f"{day_i.month:02d}-{day_i.day:02d}"]
            rate_i = list(row_i["rate"])[0]
            obj_i = {
                "date": day_i,
                "precip": round(precip * rate_i, 2),
            }
            day_i += dt.timedelta(days=1)
            result.append(obj_i)
    return result


@router_1.get('/weather_predict')
def weather_predict():
    """
    返回未来30天的降水量，单位:mm
    \n:return:
    """
    precip_list = [{"date": i["fxDate"], "precip": i["precip"]} for i in request_weather()["daily"]]
    return {'precipitation': precip_list}


@router_1.post('/mid_long_inflow_predict')
def series_predict(upload_file: UploadFile, ):
    """
    中长期来水预报
    :param upload_file: csv文件， 包含'time', 'inflow', 代表日期，来水量单位"m³/s"
    :return: 旬月年的中长期预测序列
    """
    df = pd.read_csv(upload_file.file)
    inflow_series = list(df['inflow'])
    time_series = list(df['time'])
    data = {
        'inflow': inflow_series,
        'time': time_series,
    }
    last_row = df.iloc[-1]
    predict_last_date = dt.datetime.now() + dt.timedelta(days=365)
    result = sarima_predict(data, predict_last_date)
    predict_inflow_list = []
    now = dt.datetime.now()
    for i in result:
        predict_inflow_list.append({
            "date": now.strftime("%Y-%m-%d"),
            "inflow": i,
        })
        now = now + dt.timedelta(days=1)
    print(len(predict_inflow_list))
    result = {}
    inflow_pre_10days = sum_data_to_10days(predict_inflow_list, "inflow")

    inflow_monthly = []
    inflow_yearly = []
    df = pd.DataFrame(inflow_pre_10days)
    df['ym'] = None
    df['y'] = None
    for index, row in df.iterrows():
        df.at[index, 'ym'] = row['date'][:7]  # 左闭右开
        df.at[index, 'y'] = row['date'][:4]
    group_ms = df.groupby('ym')
    for index, group_m in group_ms:
        inflow = sum(list(group_m["inflow"]))
        inflow_monthly.append({
            "date": index,
            "inflow": round(inflow, 1),
        })
    group_ys = df.groupby('y')
    for index, group_y in group_ys:
        inflow = sum(list(group_y["inflow"]))
        inflow_yearly.append({
            "date": index,
            "inflow": round(inflow, 1),
        })
    result['旬数据（单位：m³）'] = inflow_pre_10days
    result['月数据（单位：m³）'] = inflow_monthly
    result['年数据（单位：m³）'] = inflow_yearly

    return result


@router_1.post('/upload_data_file')
async def upload_data_file(upload_file: UploadFile = File(...)):
    """
    上传历史数据.csv
    \n:param upload_file: 选择文件
    \n:return: 上传成功的路径，用于未来来水的预测
    """
    if not upload_file:
        return {'error': '请上传文件'}
    content = await upload_file.read()
    with open("config/configuration_local.yaml", 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)['model1']
    save_dir = config['data-dir']
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    # 如果是按天的数据，计算得到按月的数据：
    full_path = os.path.join(save_dir, upload_file.filename)
    with open(full_path, 'wb') as f:
        f.write(content)
    # 如果是天的，转化成按月的
    sum_monthly_series(full_path)

    return {"file_dir": full_path}
