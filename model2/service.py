import json

from fastapi import APIRouter
import datetime as dt

from model2.main import request_smi_predict, request_smi_experiential

router_2 = APIRouter(
    prefix="/model2",
    tags=["需水预测模型"]
)


@router_2.get('/water_predict')
def water_predict(plant_day, begin_day, end_day, kind):
    """
    需水预测
    :param plant_day: 种植日期
    :param begin_day: 开始日期
    :param end_day: 结束日期
    :param kind: 作物类型，枚举["wheat", "corn", "cotton", "vegetable", "peanut"]
    :return: 给出单株植物每日需水序列以及总需水量
    """
    plant_d = dt.datetime.strptime(plant_day, "%Y-%m-%d")
    begin_d = dt.datetime.strptime(begin_day, "%Y-%m-%d")
    ed = dt.datetime.strptime(end_day, "%Y-%m-%d")
    td = dt.datetime.today()
    ed_former = ed
    bg_latter = ed
    if ed - td > dt.timedelta(days=30):  # 如果超过30天
        ed_former = td + dt.timedelta(days=30)
        bg_latter = ed_former + dt.timedelta(days=1)

    former_res_list = request_smi_predict(plant_d, begin_d, ed_former, kind)
    latter_res_list = request_smi_experiential(plant_d, bg_latter, ed, kind)
    if not type(former_res_list) is list or not type(latter_res_list) is list:
        return {
            "error": "<UNK>"
        }
    former_res_list.extend(latter_res_list)
    sum_smi = 0.0
    for i in former_res_list:
        sum_smi += int(i['smi'])
    return json.dumps({
        "all": sum_smi,
        "smi_list": former_res_list
    })
