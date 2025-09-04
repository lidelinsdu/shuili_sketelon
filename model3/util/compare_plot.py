import matplotlib.pyplot as plt
import pandas as pd
import requests

# 对比预测值与历史平均值，及实际值
if __name__ == '__main__':
    params = {
        "file_path": "model1/data/monthly_precip_2025-07-23-for-test.csv",
        "predict_steps": 12,
        "predict_begin_date": "2023-1-1"
    }
    predict = requests.get("http://127.0.0.1:8081/model1/inflow_predict", params=params).json()
    forecast = predict["forecast_inflow"]
    df = pd.DataFrame(forecast)
    ave_list = [7.73,
                18.57,
                15.01,
                48.74,
                65.64,
                117.41,
                267.14,
                177.87,
                79.23,
                26.27,
                36.31,
                10.4, ]
    real_list2024 = []
    with open('D:\\weather_data\\history_data\\2024.csv', 'r', encoding='utf-8') as f:
        df_real = pd.read_csv(f)
    year = 2024
    for month in range(1, 13):
        pattern = f"{year}/{month}/"
        rows = df_real[df_real["DATE"].map(lambda d: d[:7] == pattern)]
        list_row = [i * 25.4 if abs(i - 999.9) > 0.1 else 0.0
                    for i in list(rows["PRCP"])]
        real_list2024.append(sum(list_row))
    year = 2023
    real_list2023 = []
    with open('D:\\weather_data\\history_data\\2023.csv', 'r', encoding='utf-8') as f:
        df_real = pd.read_csv(f)
    for month in range(1, 13):
        pattern = f"{year}-{month:02d}-"
        rows = df_real[df_real["DATE"].map(lambda d: d[:8] == pattern)]
        list_row = [i * 25.4 if abs(i - 999.9) > 0.1 else 0.0
                    for i in list(rows["PRCP"])]
        real_list2023.append(sum(list_row))
    # 设置中文字体和负号显示
    plt.rcParams['font.sans-serif'] = ['SimHei']
    plt.rcParams['axes.unicode_minus'] = False

    # 绘制折线图
    plt.plot(list(df["date"]), list(df["predict_precip"]), label='预测值')
    plt.plot(list(df["date"]), ave_list, label='历史平均值')
    plt.plot(list(df["date"]), real_list2024, label='2024实际值')
    plt.plot(list(df["date"]), real_list2023, label='2023实际值')
    plt.xlabel('X轴标签')
    plt.ylabel('Y轴标签')
    plt.title('折线图标题')
    plt.legend()
    plt.show()
