import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

def sarima(data):
    # 使用传入的数据
    precipitation = data['precipitation'].values
    inflow = data['inflow'].values
    time = data['time'].values

    # 创建降雨量的 SARIMA 模型并拟合数据
    model_precipitation = SARIMAX(precipitation, order=(1, 0, 0), seasonal_order=(1, 0, 0, 12))
    model_precipitation_fit = model_precipitation.fit()

    # 进行未来3年降雨量的预测，并将预测结果取整
    forecast_precipitation = model_precipitation_fit.forecast(steps=3).astype(int).tolist()

    # 创建来水量的 SARIMA 模型并拟合数据
    model_inflow = SARIMAX(inflow, order=(1, 0, 0), seasonal_order=(1, 0, 0, 12))
    model_inflow_fit = model_inflow.fit()

    # 进行未来3年来水量的预测，并将预测结果保留一位小数
    forecast_inflow = np.round(model_inflow_fit.forecast(steps=3), 1).tolist()

    # 将预测结果整理成 JSON 格式
    json_data = {
        'precipitation': precipitation.tolist(),
        'inflow': inflow.tolist(),
        'time': time.tolist(),
        'forecast_precipitation': forecast_precipitation,
        'forecast_inflow': forecast_inflow,
    }

    return json_data

def sarima_path(file_path, predict_days=15):
    # 从文件中读取数据
    data = pd.read_csv(file_path)
    # 使用传入的数据
    precipitation = data['precipitation'].values
    inflow = data['inflow'].values
    time = data['time'].values

    # 创建降雨量的 SARIMA 模型并拟合数据
    model_precipitation = SARIMAX(precipitation, order=(1, 0, 0), seasonal_order=(1, 0, 0, 12))
    model_precipitation_fit = model_precipitation.fit()

    # 进行未来3年降雨量的预测，并将预测结果取整
    # forecast_precipitation = model_precipitation_fit.forecast(steps=3).astype(int).tolist()

    # 创建来水量的 SARIMA 模型并拟合数据
    model_inflow = SARIMAX(inflow, order=(1, 0, 0), seasonal_order=(1, 0, 0, 12))
    model_inflow_fit = model_inflow.fit()

    # 进行未来3年来水量的预测，并将预测结果保留一位小数
    forecast_inflow = np.round(model_inflow_fit.forecast(steps=predict_days), 1).tolist()

    # 将预测结果整理成 JSON 格式
    json_data = {
        'precipitation': precipitation.tolist(),
        'inflow': inflow.tolist(),
        'time': time.tolist(),
        # 'forecast_precipitation': forecast_precipitation,
        'forecast_inflow': forecast_inflow,
    }

    return json_data