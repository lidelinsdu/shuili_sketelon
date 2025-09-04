import datetime as dt

from fastapi import APIRouter

from model2.main import request_smi_predict, request_smi_experiential

router_2 = APIRouter(
    prefix="/model2",
    tags=["需水预测模型"]
)


@router_2.get('/water_predict')
def water_predict(plant_day, begin_day, end_day, kind):
    """
    需水预测
    \n:param plant_day: 种植日期 格式为： %Y-%m-%d  下同
    \n:param begin_day: 开始日期
    \n:param end_day: 结束日期
    \n:param kind: 作物类型，枚举["wheat", "corn", "cotton", "vegetable", "peanut"]，依次是：【小麦， 玉米， 棉花， 蔬菜（以菠菜为代表）， 花生】
    \n:return: 给出单株植物每日需水序列以及总需水量， all（总需水量）: xx.xx mm（毫米）， smi-list(每日需水量)中的单元：{'date': xx.xx}单位：毫米
    """
    plant_d = dt.datetime.strptime(plant_day, "%Y-%m-%d")
    begin_d = dt.datetime.strptime(begin_day, "%Y-%m-%d")
    ed = dt.datetime.strptime(end_day, "%Y-%m-%d")
    td = dt.datetime.today()
    ed_former = ed
    bg_latter = ed
    if ed - td > dt.timedelta(days=30):  # 如果超过30天
        ed_former = td + dt.timedelta(days=30)
        bg_latter = ed_former

    former_res_list = request_smi_predict(plant_d, begin_d, ed_former, kind)
    latter_res_list = request_smi_experiential(plant_d, bg_latter, ed, kind)

    if ed - begin_d > dt.timedelta(days=30):
        if not type(former_res_list) is list or not type(latter_res_list) is list:
            # 大于三十天时，两个变量应该都有预测值，都是list，有一个不是则计算失败
            return {"error": f"计算失败最近30天：{former_res_list}\n30天以后：{latter_res_list}"}
    else:
        if not type(former_res_list) is list:
            # 小于30天第二个变量不是list
            return {"error": f"计算失败：{former_res_list}"}

    former_res_list.extend(latter_res_list)
    sum_smi = 0.0

    for i in former_res_list:
        if type(i) is dict and 'smi' in i:
            sum_smi += float(i['smi'])

    return {
        "all": round(sum_smi, 1),
        "smi_list": former_res_list
    }

