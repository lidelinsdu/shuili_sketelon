import json

import pandas as pd


# 计算历史20年数据中，每一天占当前月份的占比
def generate_daily_rate():
    with open("../data/ave_precip.json", 'r', encoding="utf-8") as f:
        data = json.load(f)
    precip_daily = pd.DataFrame(list(data.items()), columns=['date', 'precip'])
    ave_list = []
    for month in range(1, 13):
        rows = precip_daily[precip_daily["date"].map(lambda date: date[:3] == f"{month:02d}-")]
        list_rate = list(rows["precip"])
        ave_list.append(round(sum(list_rate), 6))

    rate_list = []
    for i in range(len(ave_list)):
        month_precip = ave_list[i]
        month = i + 1
        rows = precip_daily[precip_daily["date"].map(lambda date: date[:3] == f"{month:02d}-")]
        for index, row in rows.iterrows():
            date = row["date"]
            precip = row["precip"]
            rate = round(precip / month_precip, 10)
            rate_list.append({'date': date, 'precip': precip, 'rate': rate})

    with open("../data/daily_rate.json", 'w', encoding="utf-8") as f:
        json.dump(rate_list, f, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    #generate_daily_rate()
    with open("../data/daily_rate.json", 'r', encoding="utf-8") as f:
        rate_list = json.load(f)
    precip_daily = pd.DataFrame(rate_list)

    for month in range(1, 13):
        rows = precip_daily[precip_daily["date"].map(lambda date: date[:3] == f"{month:02d}-")]
        list_rate = list(rows["rate"])
        print(f"{month}: {sum(list_rate)}")
