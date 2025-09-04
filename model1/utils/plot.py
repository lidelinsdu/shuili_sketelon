import matplotlib.pyplot as plt
import pandas as pd

# 设置中文字体和负号显示
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 读取CSV文件
data = pd.read_csv("../data/monthly_precip_2025-07-23-for-test.csv")

# 打印数据
print(data)

# 绘制折线图
plt.plot(data['time'], data['inflow'], label='Label')
plt.xlabel('X轴标签')
plt.ylabel('Y轴标签')
plt.title('折线图标题')
plt.legend()
plt.show()