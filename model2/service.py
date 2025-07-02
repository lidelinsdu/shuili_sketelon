from fastapi import APIRouter
import datetime as dt

from model2.main import request_E

router_2 = APIRouter(
    prefix="/model2",
    tags=["需水预测模型"]
)

@router_2.get('/water_predict')
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
