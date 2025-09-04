# 计算历史2005~2024 20年的平均每天降雨
import datetime as dt
import os

import pandas as pd

WEATHER_DATA_DIR = "D:\\weather_data\\history_data\\"
SAVE_DIR = "../data/"


def construct_time_series():
    """
    历史每日数据序列
    :return:
    """
    list_date = []
    list_precip = []

    for year in range(2005, 2025):
        day_cursor = dt.datetime.strptime(f"{year}-1-1", "%Y-%m-%d")
        df = pd.read_csv(f"{WEATHER_DATA_DIR}{year}.csv")
        days = len(df)
        for i in range(days):
            row = df.loc[i]
            list_date.append(row["DATE"])
            if abs(row['PRCP'] - 99.99) < 0.01:
                list_precip.append(round(row["PRCP"] * 0, 2))
            else:
                list_precip.append(round(row["PRCP"] * 25.4, 2))

    result = pd.DataFrame({"time": list_date, "inflow": list_precip})
    filename = dt.datetime.now().strftime("%Y-%m-%d") + ".csv"
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)
    result.to_csv(f"{SAVE_DIR}precip_data_{filename}")


def sum_monthly_series(filepath):
    """
    历史每月数据序列
    :return:
    """
    list_month = []  # 2005-1
    list_precip = []
    df = pd.read_csv(filepath)
    min_date = dt.datetime.strptime(df["time"].min(), "%Y-%m-%d")
    max_date = dt.datetime.strptime(df["time"].max(), "%Y-%m-%d")
    if not (min_date + dt.timedelta(days=1)).strftime("%Y-%m-%d") in list(df["time"]):
        return  # 如果不是按天的，无需计算，直接返回
    for i in range(min_date.year, max_date.year + 1):
        for month in range(1, 13):
            pattern = f"{i}-{month:02d}"
            month_rows = df[df["time"].map(lambda x: x[:7] == pattern)]
            if len(month_rows) > 0:
                sum_month = sum(list(month_rows["inflow"]))
                list_precip.append(round(sum_month, 2))
                list_month.append(pattern + "-01")
    result = pd.DataFrame({"time": list_month, "inflow": list_precip, })
    result.to_csv(filepath, index=False)
#
#
# if __name__ == '__main__':
#     sum_monthly_series()
