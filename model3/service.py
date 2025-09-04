import json

import yaml
from fastapi import APIRouter

from model3.implement import calculate_10days_allocation, calculate_monthly_allocation, calculate_yearly_allocation
import utils.file_path_processor
router_3 = APIRouter(
    prefix="/model3",
    tags=["水资源配置模型"]
)


@router_3.post("/get_allocation_for_each_area")
def get_allocation_for_each_area(water_requirement_json: list[dict], predict_inflow: dict):
    """
    获取每个灌片的配水量
    \n:param predict_inflow: 预测的未来12个月每天的降雨量list[dict]
    \n:param water_requirement_json: 各个灌片需水的数据list[dict]
    \n 注意： 需水数据需要和来水数据的日期对应起来。没有来水默认来水为0
    \n:return: 旬、月、年度每个灌片所需的配水量
    """
    # 确定好时间段， 以旬为单位~！！！！
    # 灌区信息： 灌区名称，ID，灌区需水量 mm， 灌区面积 ㎡， 灌区每日降水量 mm,
    # 最后根据计算每旬的得到每月，每年的配水量信息。
    # 灌区配水量 = （灌区需水量（mm） - 灌区来水量（mm）） * 灌区面积 = m³
    with open("config/configuration_local.yaml", 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)['model3']

    area_info_file = config['area-info-file']
    with open(area_info_file, 'r', encoding='utf-8') as f:
        area = json.load(f)

    # 计算来水
    allocations_10days = calculate_10days_allocation(water_requirement_json, predict_inflow, area)
    allocations_monthly = calculate_monthly_allocation(allocations_10days)
    allocations_yearly = calculate_yearly_allocation(allocations_10days)
    return {
        "per_10days": allocations_10days,
        "monthly": allocations_monthly,
        "yearly": allocations_yearly,
    }
