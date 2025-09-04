import datetime as dt
import json

import pandas as pd


def calculate_10days_allocation(water_demand_data, inflow_data, area_info):
    """
    计算逐旬各个灌区配水量
    :param area_info: 灌区数据列表，每个灌区对应一个json， area_info是   list[dict]
    :param water_demand_data: 十个灌区需水叙述
    :param inflow_data:  灌区预测来水数据
    :return: obj_list: []
    obj: {"name": "灌区名称",
          "allocations": [allocation],
                  allocation: {
                        time_begin: date,
                        time_end: date,
                        allocate_water: mm
                        }
          }
    """
    inflow_data_per_10days = sum_data_to_10days(inflow_data['forecast_inflow'], 'precip')
    inflow_df = pd.DataFrame(inflow_data_per_10days)
    # 完成十日需水处理：
    result = []
    for i in water_demand_data:
        area_name = i['area_name']  # 灌区名称
        result_i = []
        demand_per_10days = sum_data_to_10days(i["water_demand"], "smi")
        area = area_info[area_name]["area"] * 666.7
        for x in demand_per_10days:
            time, demand = x.values()
            _inflow = list(inflow_df[inflow_df['date'] == time]['precip'])
            if len(_inflow) > 0:
                allocation = demand - _inflow[0]
            else:
                allocation = demand
            result_i.append({
                "date": time,
                "allocation": round(max(0, allocation * 0.001 * area), 1),
            })
        result.append({
            "area_name": area_name,
            "allocations": result_i,
        })
    return result


def calculate_monthly_allocation(allocation_per_10days):
    """
    计算每月的配水量
    :param allocation_per_10days: 逐旬配水量
    :return: 逐月配水量
    """
    result = []
    for i in allocation_per_10days:
        area_name = i['area_name']
        allocations = i['allocations']
        result_i = []
        df = pd.DataFrame(allocations)
        df['ym'] = None
        for index, row in df.iterrows():
            df.at[index, 'ym'] = row['date'][:7]
        group = df.groupby('ym')
        for index, group in group:
            allocation = sum(list(group["allocation"]))
            result_i.append({
                "date": index,
                "allocation": round(allocation, 1),
            })

        result.append({
            "area_name": area_name,
            "allocations": result_i,
        })

    return result


def calculate_yearly_allocation(allocation_per_10days):
    """
        计算每年的配水量
        :param allocation_per_10days: 逐旬配水量
        :return: 逐月配水量
        """
    result = []
    for i in allocation_per_10days:
        area_name = i['area_name']
        allocations = i['allocations']
        result_i = []
        df = pd.DataFrame(allocations)
        df['y'] = None
        for index, row in df.iterrows():
            df.at[index, 'ym'] = row['date'][:4]
        group = df.groupby('ym')
        for index, group in group:
            allocation = sum(list(group["allocation"]))
            result_i.append({
                "date": index,
                "allocation": round(allocation, 1),
            })

        result.append({
            "area_name": area_name,
            "allocations": result_i,
        })

    return result


def sum_data_to_10days(json_list, value_name):
    """
    将一整年日数据转换为旬数据
    必须要传入一整年的数据
    :param value_name: 数据名称， smi ， precip
    :param json_list:[{'date':---, 'value_name':---},{},{}...]
    :return: 按旬的数据
    """
    value_10days = {}
    df = pd.DataFrame(json_list)

    min_date = dt.datetime.strptime(min(df["date"]), '%Y-%m-%d')
    max_date = dt.datetime.strptime(max(df["date"]), '%Y-%m-%d')

    day_i = min_date
    sum_value = 0
    while day_i < max_date:
        if day_i.day == 1 or day_i.day == 11 or day_i.day == 21:
            sum_value = 0  # 分界线处清空
        month = day_i.month
        year = day_i.year
        key = f"{year}-{month:02d}-"
        day = day_i.day
        day_i_str = day_i.strftime("%Y-%m-%d")
        value_list = list(df[df["date"] == day_i_str][value_name])
        try:
            value = value_list[0]
        except IndexError:
            print(f"计算{value_name}时，日期{day_i_str}缺失")
            return "计算失败"
        if 1 <= day <= 10:
            sum_value += value
            key += "上旬"
        elif 11 <= day <= 20:
            sum_value += value
            key += "中旬"
        else:
            sum_value += value
            key += "下旬"
        value_10days[key] = round(sum_value, 2)
        day_i += dt.timedelta(days=1)

    return [{"date": key, value_name: value} for key, value in value_10days.items()]


if __name__ == '__main__':
    with open('../model3/data/water_demand.json', 'r', encoding='utf-8') as f:
        water_requirement_json = json.load(f)

    with open('../model1/data/model1_response_2025-7-1---2025-6-30.json', 'r', encoding='utf-8') as f:
        precip_list = json.load(f)

    with open("./data/area_info.json", 'r', encoding='utf-8') as f:
        area_info = json.load(f)

    res = calculate_10days_allocation(water_requirement_json, precip_list, area_info)
    monthly_res = calculate_monthly_allocation(res)
    yearly_res = calculate_yearly_allocation(res)

    with open('.per_10days.json','w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=4)
    with open('.yearly.json','w', encoding='utf-8') as f:
        json.dump(yearly_res, f, ensure_ascii=False, indent=4)
    with open('.monthly.json','w', encoding='utf-8') as f:
        json.dump(monthly_res, f, ensure_ascii=False, indent=4)

