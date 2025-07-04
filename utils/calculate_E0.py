import datetime as dt
import os
import pandas as pd
from dateutil.relativedelta import relativedelta
from pandas import DataFrame

from model2.main import PM_ET0

# 存储历史数据的路径
# 2005~2024年，兖州监测站
WEATHER_DATA_DIR = "D:\\weather_data\\history_data\\"
SAVE_E0_DIR = "E0_per_day\\"


def f_to_c(f):
    """
    华氏度转摄氏度
    :param f: 华氏度
    :return: 摄氏度
    """
    return round((float(f) - 32) / 1.8, 1)


def knots_to_mps(x):
    """
    节到mps
    :param x: 速度
    :return: mps速度
    """
    return round(float(x) * 0.51444444, 1)


def weather_from_csv_to_json(path, year):
    df = pd.read_csv(path)
    date = df["DATE"].tolist()  # 日期
    max_f_temp = df["MAX"].tolist()  # 最高华氏度
    max_c_temp = [f_to_c(i) for i in max_f_temp]
    min_f_temp = df["MIN"].tolist()  # 最低华氏度
    min_c_temp = [f_to_c(i) for i in min_f_temp]
    wind_speed_in_knots = df["WDSP"].tolist()  # 平均风速
    wind_speed_in_mps = [knots_to_mps(i) for i in wind_speed_in_knots]
    pressure = df["SLP"].tolist()  # 平均气压
    # 日照时间从data.json文件中读取

    new_df = DataFrame({"date": date,
                        "max_c_temp": max_c_temp,
                        "min_c_temp": min_c_temp,
                        "wind_speed_in_mps": wind_speed_in_mps,
                        "pressure": pressure, })
    return year, new_df


def do_main_calculate():
    for year in range(2005, 2025):
        year, df = weather_from_csv_to_json(WEATHER_DATA_DIR + f"{year}.csv", year)
        e0_list = pd.DataFrame(columns=["date", "E0"])
        for index, row in df.iterrows():
            date = row["date"]
            max_t = row["max_c_temp"]
            min_t = row["min_c_temp"]
            u2 = row["wind_speed_in_mps"]
            p = row["pressure"]
            e0 = PM_ET0(max_t, min_t, p, u2, year, dt.datetime.now())
            e0_list.loc[len(e0_list)] = [date, e0]
        e0_list.to_csv(f"{SAVE_E0_DIR}{year}_E0.csv", index=False)


def ave_e0():
    save_file_dir = f"ave_e0.csv"
    fn_list = []
    weight = []  ## 添加权重， 后十年占多0.2
    for i in range(20):
        if i < 10:
            weight.append(0.9)
        else:
            weight.append(1.1)
    print(sum(weight))
    for path, _, files in os.walk(SAVE_E0_DIR):
        for file in files:
            filename = os.path.join(path, file)
            fn_list.append((int(file[:4]), filename))
    ave_e0_list = pd.DataFrame(columns=["date", "E0_ave"])
    for d in iterate_year_days():
        print(f"处理日期{d}")
        e0_sum = 0.0
        count = 0.0
        for year, filename in fn_list:
            # print(f"处理文件{filename}")
            i = (year-2024)+19
            data = pd.read_csv(filename)
            for index, row in data.iterrows():
                f_date = dt.datetime.strptime(row["date"], "%Y-%m-%d")
                target_date = d - relativedelta(years=(2024 - year))
                if f_date == target_date:
                    e0_sum += row["E0"] * weight[i]
                    count += weight[i]
                    break
        ave = round(e0_sum / count, 4)
        ave_e0_list.loc[len(ave_e0_list)] = [d, ave]
    ave_e0_list.to_csv(save_file_dir, index=False)


def iterate_year_days(year=2024):
    # 定义起始日期
    start_date = dt.datetime(year=year, month=1, day=1)
    # 结束日期为下一年的第一天，这样循环时能包含当年最后一天
    end_date = dt.datetime(year=year + 1, month=1, day=1)

    current_day = start_date
    while current_day < end_date:
        yield current_day  # 以生成器方式返回每天的日期
        current_day += dt.timedelta(days=1)


if __name__ == "__main__":
    # do_main_calculate()
    ave_e0()
