from fastapi import APIRouter
import sys
import model3.main

router_3 = APIRouter(
    prefix="/model3",
    tags=["水资源配置模型"]
)

'''
python main.py --mode annual --year 2019 --data data1.xlsx
生成2019年年度水资源配置方案
python main.py --mode monthly --year 2019 --month 7 --data data1.xlsx
生成2019年1月月度水资源配置方案
python main.py --mode dekad --year 2019 --month 1 --dekad 1 --data data1.xlsx
生成2019年1月上旬(第1旬)水资源配置方案

参数
--mode：运行模式，可选值为 annual（年度）、monthly（月度）、dekad（旬）
--year：年份（如 2019）
--month：月份（1-12，仅在 monthly 和 dekad 模式下需要）
--dekad：第几旬（1-3[上中下]，仅在 dekad 模式下需要）
--data：输入数据文件名（如 data1.xlsx）

data1.xlsx需包含信息：
每日供水量：每天的各个水源的可供水量
每日需水量：每天的各个节点/灌区的需水量
灌区信息：
水源关系：水源直接连接节点的信息，例水源A直接连接节点N1，也就是A能直接输送水到N1，不用经过其他节点
注意：原始数据不包含水源信息
'''


@router_3.get("/get_allocate_xlsx")
def get_allocate_xlsx(time_range: str, year: int, data: str, month: int = -1, dekad: int = -1, ):
    """
    获取水资源配置方案，结果以xlsx文件保存
    :param time_range: 时间范围，枚举类型：[annual, monthly, dekad]
    :param year: 整数类型
    :param month: 整数类型 1-12
    :param dekad:整数类型 1-3 分别代表上、中、下旬
    :param data: 文件路径，文件格式根据提供的样式来
    :return: 文件路径
    """
    sys.argv = ["model3/main.py", "--mode", f"{time_range}", "--year", f"{year}"]

    time_range = str(time_range)
    if time_range == "monthly":
        sys.argv.append("--month")
        sys.argv.append(str(month))
    elif time_range == "dekad":
        sys.argv.append("--month")
        sys.argv.append(str(month))
        sys.argv.append("--dekad")
        sys.argv.append(str(dekad))
    elif time_range != "annual":
        return "error"

    sys.argv.append("--data")
    sys.argv.append(data)
    return model3.main.main()
