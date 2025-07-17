import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

# 设置随机种子以确保结果可重复
np.random.seed(42)
random.seed(42)

# 输出文件名
OUTPUT_FILE = "汶阳田水资源原始数据.xlsx"


def main():
    """生成水资源原始数据，精确到天，从2019年至2024年底"""
    print("开始生成水资源原始数据...")

    # 设置日期范围（6年）
    start_date = datetime(2019, 1, 1)
    end_date = datetime(2024, 12, 31)

    # 生成所有日期
    dates = []
    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=1)

    # 定义灌区和水源
    districts = ["张安水库提水灌区", "张安水库自流灌区", "安驾庄镇漕浊河提水灌区","机井灌区","北仇水库提水灌区","红石金渠道提水灌区","营盘水库提水灌区","魏庄泵站提水管区","浊河提水灌区","边院镇漕浊河堤水管区"]
    water_sources = ["浊河水", "地下水", "水库水", "泵站调水"]

    # 创建Excel写入器
    writer = pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl')

    # 1. 每日供水量数据
    daily_supply = pd.DataFrame(index=dates)

    # 为每个水源定义特性
    source_characteristics = {
        "浊河水": {
            "base_supply": 56.7,  # 较高的基础供水能力
            "seasonal_variance": 0.25,  # 受季节影响较大
            "drought_sensitivity": 0.7,  # 较高的干旱敏感度
            "trend": 0.005  # 年均递减趋势（水资源紧张）
        },
        "地下水": {
            "base_supply": 26.8,
            "seasonal_variance": 0.1,  # 受季节影响较小
            "drought_sensitivity": 0.3,  # 短期干旱影响较小
            "trend": -0.01  # 年均递减趋势（过度开采导致水位下降）
        },
        "水库水": {
            "base_supply": 29.2,
            "seasonal_variance": 0.3,  # 季节性变化明显
            "drought_sensitivity": 0.8,  # 高干旱敏感度
            "trend": 0.003  # 水库扩建导致略微增加
        },
        "泵站调水": {
            "base_supply": 33.5,
            "seasonal_variance": 0.05,  # 季节性影响小
            "drought_sensitivity": 0.2,  # 不太受干旱影响
            "trend": 0.02  # 工程持续投入使用导致增长
        }
    }

    # 定义重大事件影响
    events = {
        "2020-06-15": {"name": "洪涝灾害", "duration": 20,
                       "sources": {"浊河水": 1.4, "水库水": 1.5, "地下水": 0.95, "泵站调水": 0.9}},
        "2020-09-01": {"name": "干旱开始", "duration": 120,
                       "sources": {"浊河水": 0.7, "水库水": 0.6, "地下水": 0.9, "泵站调水": 0.95}},
        "2021-07-20": {"name": "中度洪涝", "duration": 15,
                       "sources": {"浊河水": 1.3, "水库水": 1.4, "地下水": 0.98, "泵站调水": 0.95}},
        "2022-04-10": {"name": "泵站调水扩建", "duration": 365, "sources": {"泵站调水": 1.15}},
        "2023-05-10": {"name": "严重干旱", "duration": 90,
                       "sources": {"浊河水": 0.6, "水库水": 0.5, "地下水": 0.85, "泵站调水": 0.90}},
        "2024-03-01": {"name": "水库扩建", "duration": 300, "sources": {"水库水": 1.2}}
    }

    for source in water_sources:
        values = []
        char = source_characteristics[source]
        base_supply = char["base_supply"]

        for date_str in dates:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            month = date.month
            day = date.day
            year = date.year
            doy = date.timetuple().tm_yday  # 一年中的第几天

            # 基础季节性变化（使用正弦函数模拟）
            if source == "水库水":
                # 水库水在春季开始增加，夏末秋初达到峰值，冬季最低
                season_factor = 1.0 + char["seasonal_variance"] * np.sin((doy - 120) / 365 * 2 * np.pi)
            elif source == "浊河水":
                # 浊河水在夏季丰水期达到峰值
                season_factor = 1.0 + char["seasonal_variance"] * np.sin((doy - 180) / 365 * 2 * np.pi)
            else:
                # 其他水源的季节变化
                season_factor = 1.0 + char["seasonal_variance"] * np.sin((doy - 150) / 365 * 2 * np.pi)

            # 加入随机波动
            season_factor *= (1.0 + np.random.normal(0, 0.05))

            # 年度变化趋势（长期趋势）
            year_factor = 1.0 + char["trend"] * (year - 2019)

            # 年度气候条件
            climate_factors = {
                2019: 1.02,  # 正常气候年
                2020: 0.85,  # 干旱年
                2021: 1.05,  # 湿润年
                2022: 1.10,  # 丰水年
                2023: 0.80,  # 严重干旱年
                2024: 0.95  # 轻微干旱年
            }
            climate_factor = climate_factors[year] ** char["drought_sensitivity"]

            # 应用重大事件影响
            event_factor = 1.0
            for event_date, event in events.items():
                event_start = datetime.strptime(event_date, "%Y-%m-%d")
                event_end = event_start + timedelta(days=event["duration"])

                if event_start <= date <= event_end and source in event["sources"]:
                    event_factor *= event["sources"][source]

            # 随机日常波动
            daily_factor = 1.0 + np.random.normal(0, 0.04)

            # 计算最终供水量并确保非负
            supply = max(0, base_supply * season_factor * year_factor * climate_factor * event_factor * daily_factor)

            # 数值取整（保留2位小数）
            values.append(round(supply, 2))

        daily_supply[source] = values

    daily_supply.to_excel(writer, sheet_name="每日供水量")

    # 2. 每日需水量数据
    daily_demand = pd.DataFrame(index=dates)

    # 为每个灌区定义特性
    district_characteristics = {
        "张安水库提水灌区": {
            "base_demand": 9.0,
            "crop_pattern": "早熟",  # 提水灌区通常支持早熟高产作物
            "growth_rate": 0.028,
            "industrial_ratio": 0.25,  # 水库支持一定工业用水
        },
        "张安水库自流灌区": {
            "base_demand": 7.5,
            "crop_pattern": "多样化",  # 自流灌区种植较为灵活
            "growth_rate": 0.022,
            "industrial_ratio": 0.15,  # 工业用水比例较低
        },
        "安驾庄镇漕浊河提水灌区": {
            "base_demand": 8.2,
            "crop_pattern": "早熟",  # 河流水源支持早熟作物
            "growth_rate": 0.030,
            "industrial_ratio": 0.20,  # 城镇附近有一定工业需求
        },
        "机井灌区": {
            "base_demand": 6.5,
            "crop_pattern": "晚熟",  # 地下水灌溉常用于晚熟作物
            "growth_rate": 0.018,
            "industrial_ratio": 0.10,  # 农业为主，工业用水少
        },
        "北仇水库提水灌区": {
            "base_demand": 8.8,
            "crop_pattern": "早熟",  # 水库提水支持高产早熟作物
            "growth_rate": 0.027,
            "industrial_ratio": 0.22,  # 适中的工业用水比例
        },
        "红石金渠道提水灌区": {
            "base_demand": 7.8,
            "crop_pattern": "多样化",  # 渠道灌溉支持多种作物
            "growth_rate": 0.025,
            "industrial_ratio": 0.18,  # 渠道灌区有一定工业用水
        },
        "营盘水库提水灌区": {
            "base_demand": 9.2,
            "crop_pattern": "早熟",  # 水库提水支持早熟作物
            "growth_rate": 0.029,
            "industrial_ratio": 0.24,  # 较高的工业用水比例
        },
        "魏庄泵站提水管区": {
            "base_demand": 8.0,
            "crop_pattern": "多样化",  # 泵站支持灵活种植
            "growth_rate": 0.026,
            "industrial_ratio": 0.20,  # 泵站附近有工业需求
        },
        "浊河提水灌区": {
            "base_demand": 7.0,
            "crop_pattern": "晚熟",  # 河流水质可能适合晚熟作物
            "growth_rate": 0.020,
            "industrial_ratio": 0.12,  # 农业为主，工业用水少
        },
        "边院镇漕浊河堤水管区": {
            "base_demand": 7.3,
            "crop_pattern": "多样化",  # 堤防灌区种植多样
            "growth_rate": 0.023,
            "industrial_ratio": 0.15,  # 城镇附近工业用水较低
        }
    }

    for district in districts:
        values = []
        char = district_characteristics[district]
        base_demand = char["base_demand"]

        for date_str in dates:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            month = date.month
            day = date.day
            year = date.year
            doy = date.timetuple().tm_yday  # 一年中的第几天

            # 基于作物模式的季节性变化
            if char["crop_pattern"] == "早熟":
                # 早熟作物在春季有较高需水量
                peak_day = 120  # 4月底左右
            elif char["crop_pattern"] == "晚熟":
                # 晚熟作物在夏末有较高需水量
                peak_day = 240  # 8月底左右
            else:
                # 多样化种植有较为平缓的需水曲线
                peak_day = 180  # 6月底左右

            # 使用高斯分布模拟生长季需水量
            days_from_peak = min(abs(doy - peak_day), abs(doy - peak_day - 365), abs(doy - peak_day + 365))
            season_factor = 1.0 + 0.9 * np.exp(-(days_from_peak ** 2) / (2 * (90 ** 2)))

            # 工业用水较为稳定
            industrial_component = char["industrial_ratio"] * base_demand * (1.0 + np.random.normal(0, 0.03))
            # 农业用水受季节影响大
            agricultural_component = (1 - char["industrial_ratio"]) * base_demand * season_factor * (
                        1.0 + np.random.normal(0, 0.08))

            # 年度增长
            year_growth = 1.0 + char["growth_rate"] * (year - 2019)

            # 考虑气候因素对需水量的影响
            # 干旱年份需水量增加
            climate_factors = {
                2019: 1.0,  # 正常气候年
                2020: 1.15,  # 干旱年，需水量增加
                2021: 0.95,  # 湿润年，需水量减少
                2022: 0.9,  # 丰水年，需水量减少
                2023: 1.25,  # 严重干旱年，需水量大增
                2024: 1.1  # 轻微干旱年，需水量略增
            }

            # 每周模式（工作日vs周末）影响工业用水
            weekday = date.weekday()
            weekday_factor = 1.0 - char["industrial_ratio"] * 0.15 * (1 if weekday >= 5 else 0)  # 周末工业用水减少

            # 节假日因素
            holiday_factor = 1.0
            # 春节前后
            spring_festival_dates = {
                2019: (datetime(2019, 2, 4), datetime(2019, 2, 10)),
                2020: (datetime(2020, 1, 24), datetime(2020, 1, 30)),
                2021: (datetime(2021, 2, 11), datetime(2021, 2, 17)),
                2022: (datetime(2022, 1, 31), datetime(2022, 2, 6)),
                2023: (datetime(2023, 1, 21), datetime(2023, 1, 27)),
                2024: (datetime(2024, 2, 10), datetime(2024, 2, 16))
            }

            if year in spring_festival_dates:
                sf_start, sf_end = spring_festival_dates[year]
                if sf_start <= date <= sf_end:
                    holiday_factor = 0.85  # 春节期间需水量减少

            # 计算最终需水量
            climate_factor = climate_factors[year]
            demand = (
                                 industrial_component + agricultural_component) * year_growth * climate_factor * weekday_factor * holiday_factor

            # 确保非负并保留两位小数
            values.append(round(max(0, demand), 2))

        daily_demand[district] = values

    daily_demand.to_excel(writer, sheet_name="每日需水量")

    # 3. 基础信息表
    # 灌区信息（增加了更详细的数据）
    district_info = pd.DataFrame({
        "灌区名称": districts,
        "总面积(亩)": [10386, 2318, 5605, 7144, 8369, 6699, 2508, 9474, 36683, 11049],  # 10 个值
        "耕地面积(公顷)": [2800, 3360, 2240, 2560, 2880, 2400, 3040, 2720, 2320, 2480],  # 10 个值
        "灌溉效率(%)": [65, 70, 62, 68, 66, 64, 69, 67, 63, 65],  # 10 个值
        "主要作物": [
            "小麦、玉米", "水稻、小麦、蔬菜", "棉花、玉米", "小麦、蔬菜",
            "玉米、水稻", "小麦、棉花", "水稻、玉米", "小麦、果树",
            "玉米、蔬菜", "棉花、水稻"
        ],  # 10 个值
        "人口(万人)": [12.5, 18.2, 9.8, 10.5, 13.0, 11.2, 14.5, 12.0, 10.8, 11.5],  # 10 个值
        "工业用水比例(%)": [25, 15, 20, 10, 22, 18, 24, 20, 12, 15]  # 与 district_characteristics 一致
    })
    district_info.to_excel(writer, sheet_name="灌区信息", index=False)

    # 水源信息（增加了更详细的数据）
    source_info = pd.DataFrame({
        "水源名称": water_sources,
        "最大供水能力(万m³/日)": [60, 30, 30, 20],
        "单位水成本(元/m³)": [0.2, 0.5, 0.3, 0.7],
        "优先级": [1, 3, 2, 4],
        "水质等级": ["II类", "III类", "II类", "II类"],
        "可靠性评分": [80, 95, 75, 90],
        "年均可供水量(亿m³)": [3.2, 1.8, 2.5, 1.5]
    })
    source_info.to_excel(writer, sheet_name="水源信息", index=False)

    # 保存Excel文件
    writer.close()

    print(f"数据生成完成，已保存至 {OUTPUT_FILE}")
    print(f"包含2019-01-01至2024-12-31共6年的每日水资源数据")


if __name__ == "__main__":
    main()