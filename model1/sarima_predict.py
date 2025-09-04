import datetime as dt

import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX


# 用按周为周期的数据预测来水序列

def sarima_predict(data, predict_end_date):
    rainfall = data['inflow']
    time = data['time']
    # 假设 data 是 pandas Series，索引为日期，值为每日降雨量
    data = pd.Series(rainfall, index=pd.date_range(start=time[0], periods=len(time)))

    data_weekly = data.resample('W-SUN').sum()
    print(f"周数据长度: {len(data_weekly)} 周")
    # 构建 SARIMAX 模型：季节周期 52（年）
    model = SARIMAX(
        data_weekly,
        order=(1, 1, 1),  # 非季节项
        seasonal_order=(1, 1, 1, 52),  # 季节项，周期52周
        enforce_stationarity=False,
        enforce_invertibility=False
    )

    # 拟合模型
    fitted = model.fit(disp=False)  # disp=False 避免输出优化过程
    print(fitted.summary())
    # 计算未来多少周
    weeks = (predict_end_date - dt.datetime.strptime(time[-1], "%Y-%m-%d")).days / 7 + 2
    forecast_weeks = fitted.get_forecast(steps=int(weeks))

    pred_weekly_mean = forecast_weeks.predicted_mean

    last_week_end = data_weekly.index[-1]  # 最后一个周结束日（2024-12-29 或 2025-01-05？）
    future_week_ends = pd.date_range(last_week_end + pd.Timedelta(days=7), periods=weeks, freq='W-SUN')

    # 构建预测周序列
    pred_weekly = pd.Series(pred_weekly_mean, index=future_week_ends)

    # 将周数据升频到每日：先 reindex 到每日，再插值
    daily_index = pd.date_range(future_week_ends[0],
                                future_week_ends[-1],
                                freq='D')

    # 但这是“每周总量”分布在7天，我们希望是“每日趋势”，所以做线性插值平滑
    # 更合理的方式：在周边界之间插值
    pred_daily_interpolated = pred_weekly.reindex(daily_index).interpolate(method='linear')

    target_start = dt.datetime.now().strftime("%Y-%m-%d")
    target_end = predict_end_date.strftime("%Y-%m-%d")

    # 筛选目标时间段
    final_prediction = pred_daily_interpolated.loc[target_start:target_end]

    print(f"预测时间段: {final_prediction.index[0]} 到 {final_prediction.index[-1]}")
    print(f"共 {len(final_prediction)} 天")
    return final_prediction


if __name__ == '__main__':
    with open('../utils/inflow_predict_data.csv', 'r', encoding='utf-8') as f:
        df = pd.read_csv(f)
    inflow_series = list(df['inflow'])
    time_series = list(df['time'])
    data = {
        'inflow': inflow_series,
        'time': time_series,
    }
    last_row = df.iloc[-1]
    last_date = dt.datetime.strptime(last_row['time'], "%Y-%m-%d")  # 预测数据最后一天
    predict_last_date = dt.datetime.now() + dt.timedelta(days=365)

    print(sarima_predict(data, predict_last_date))
