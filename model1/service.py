from fastapi import APIRouter
import time
from model1.inflow_ARIMA import arima_path
from model1.inflow_SARIMA import sarima_path
from model1.inflow_SARIMAX import sarimax_path
from model1.hefeng_weather_predict import request_weather

router_1 = APIRouter(
    prefix="/model1",
    tags=["来水预报模型"]
)

@router_1.get('/inflow_predict')
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
