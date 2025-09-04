# 计算历史2005~2024 20年的平均每天降雨
import datetime as dt
import json

from utils.calculate_E0 import weather_from_csv_to_json

WEATHER_DATA_DIR = "D:\\weather_data\\history_data\\"

day_list = {}
year_366 = dt.datetime.strptime("2024-1-1", "%Y-%m-%d")
for i in range(366):
    date_str = year_366.strftime("%Y-%m-%d")
    day_list[date_str[-5:]] = 0.0
    year_366 += dt.timedelta(days=1)

for year in range(2005, 2025):
    year, df = weather_from_csv_to_json(WEATHER_DATA_DIR + f"{year}.csv", year)
    for index, row in df.iterrows():
        part = row['date'][-5:]
        precip = row["precip"]
        if abs(precip - 99.99) < 0.1:
            day_list[part] = 0.0
        else:
            day_list[part] = day_list[part] + precip

day_list['02-29'] = day_list['02-29'] * 4
for i, j in day_list.items():
    day_list[i] = round(day_list[i] * 25.4 / 20, 3)
with open("ave_precip.json", "w", encoding='utf-8') as f:
    json.dump(day_list, f, ensure_ascii=False, indent=4)
