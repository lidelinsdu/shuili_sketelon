# 创建model1中长期来水序列的测试数据

import datetime as dt
import random

import pandas as pd

begin_date = dt.datetime(2020, 1, 1)
end_date = dt.datetime(2024, 12, 31)
day_count = (end_date - begin_date).days

result = []
random.seed(42)
for i in range(day_count):

    # 生成 1000 到 9999999 之间的随机整数
    inflow = random.randint(1000, 9999999)
    result.append({
        "time": begin_date,
        "inflow": inflow,
    })
    begin_date = begin_date + dt.timedelta(days=1)

df = pd.DataFrame(result)
df.to_csv("inflow_predict_data.csv", index=False)
