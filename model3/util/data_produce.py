import datetime as dt
import json
import random

import pandas as pd


def construct_demand_example():
    with open('../data/water_requirement_example.json', 'r', encoding='utf-8') as f:
        water_requirement_json = json.load(f)

    json_list = []
    for item in water_requirement_json:
        area_name = list(item.keys())[0]
        water_requirement = {}
        date_cursor = dt.datetime.strptime("2025-1-1", "%Y-%m-%d")
        for i in range(365):
            need_i = round(random.random(), 3)
            water_requirement[date_cursor.strftime("%Y-%m-%d")] = need_i
            date_cursor += dt.timedelta(days=1)
        json_list.append({area_name: water_requirement})
    with open('../data/water_requirement_example.json', 'w', encoding='utf-8') as f:
        json.dump(json_list, f, ensure_ascii=False, indent=4)

def construct_precip_monthly():
    with open('../data/precip_per10days.csv', 'r', encoding='utf-8') as f:
        df = pd.read_csv(f)


def construct_precip_per10days():
    with open('../data/ave_precip.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    df = pd.DataFrame(list(data.items()), columns=['date', 'precip'])
    time_list = []
    precip_list = []
    for month in range(1, 13):
        for ten_day in range(3):
            if not ten_day == 2:  # 上中旬
                rows = df[df["date"].map(
                    lambda d: d[:4] == f"{month:02d}-{ten_day:01d}" or
                              d[:5] == f"{month:02d}-{ten_day + 1:01d}0")]
                sum_precip = round(sum(list(rows["precip"])), 2)
                if ten_day == 0:  # 上旬
                    time_list.append(f"2025-{month:02d}-上旬")
                else:
                    time_list.append(f"2025-{month:02d}-中旬")
                precip_list.append(sum_precip)
            else:  # 下旬
                rows = df[df["date"].map(
                    lambda d: d[:4] == f"{month:02d}-{ten_day:01d}")]
                extra_rows = df[df["date"].map(
                    lambda date: date[:4] == f"{month:02d}-{ten_day + 1:01d}")]
                s1 = sum(list(rows["precip"]))
                s2 = sum(list(extra_rows["precip"]))
                sum_precip = s1 + s2
                sum_precip = round(sum_precip, 2)
                time_list.append(f"2025-{month:02d}-下旬")
                precip_list.append(sum_precip)
    result = pd.DataFrame({"date": time_list, "precip": precip_list})
    result.to_csv("../data/precip_per10days.csv", index=False)
    # obj = result.set_index('date')['precip'].to_dict()
    # demand_10days[area_name] = obj
    # with open('./data/demand_10days.json', 'w', encoding='utf-8') as f:
    #     json.dump(demand_10days, f, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    construct_precip_per10days()
