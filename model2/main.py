import datetime as dt
import json
import math
import re
from datetime import timedelta

import pandas
import pandas as pd

from utils.hefeng_weather_predict import request_weather

# 纬度
LAT = 35.57

"""
天文辐射 Q0计算公式
"""


def cal_Ra(year, month, day, lat=LAT):
    # year,month,day分别为年、月、日；lat为纬度;
    dn = rixu(year, month, day)
    # w = w_F(lat,DEC)
    # N = N_F(w)
    return cal_Q_Ra(dn)


"""
太阳总辐射 Q计算公式
"""


def cal_Q(Q0, Q_fact, N):
    # Q0为天文辐射；Q_fact为日照时数；N为可照时数
    n = Q_fact
    S1 = s1(n, N)

    a = 0.248
    b = 0.752
    Q = Q0 * (a + b * S1)
    return Q


"""
计算SR
"""


def SR(Tmax, Tmin, Ra, Krs=0.16):
    # 大陆条件Krs=0.16
    return Krs * Ra * (Tmax - Tmin) ** 0.5


"""
定义列表第i个数之前所有元素的和
"""


def sum_list(items, i):
    sum_numbers = 0
    c = 0
    if i == 1:
        return 0
    else:
        for x in items:
            if c != i - 1:
                sum_numbers += x
                c += 1
            else:
                break
        return sum_numbers


"""
定义日序计算方法
"""


def rixu(x, y, z):
    # x为年,y为月,z为日
    run = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    flat = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if x % 4 == 0 and x % 100 != 0:  # 判断闰年
        runnian = 1
    elif x % 400 == 0:
        runnian = 1
    else:
        runnian = 0
    if runnian == 1:
        d = sum_list(run, y) + z
    else:
        d = sum_list(flat, y) + z
    return d


"""
定义太阳赤纬计算方法
"""


def dec(rixu):
    int(rixu)
    a = 2 * math.pi * (rixu - 1) / 365.2422
    d = (0.006918 - 0.399912 * math.cos(a) + 0.070257 * math.sin(a) - 0.006758 * math.cos(2 * a)
         + 0.000907 * math.sin(2 * a) - 0.002697 * math.cos(3 * a) + 0.00148 * math.sin(3 * a))
    float('%.2f' % d)
    declination = d
    # d = math.degrees(declination)
    return declination


"""
定义时角w的算法
"""


def w_F(lat, dec):
    t = -1 * math.tan((31.56 / 360 * 2 * math.pi)) * math.tan(dec)
    w = math.acos(t)
    return w


"""
定义N的算法
"""


def N_F(w):
    N = 24 * w / math.pi
    return N


"""
定义Q0的算法
"""


def cal_Q_Ra(dn, lat=LAT, ):
    # 轨道订正系数
    # OCF = (1.00011 + 0.034221 * math.cos(TR) + 0.00128 * math.sin(TR) + 0.000719 * math.cos(2 * TR)
    #        + 0.000077 * math.sin(2 * TR))
    dr = 1 + 0.033 * math.cos(2 * math.pi * dn / 365)
    cita = 0.409 * math.sin(2 * math.pi * dn / 365 - 1.39)
    t = -1 * math.tan((LAT / 360 * 2 * math.pi)) * math.tan(cita)
    w = math.acos(t)
    lat = lat / 360 * 2 * math.pi
    Q = 24 * 60 * 0.082 * dr * (w * math.sin(lat) * math.sin(cita) + math.cos(lat) * math.cos(cita)
                                * math.sin(w)) / (math.pi)
    return Q


"""
定义S1的算法
"""


def s1(n, N):
    s = n / N
    return s


"""
净长波辐射计算公式
"""


def R_net_long(Tmax, Tmin, ea, SR, Ra):  # Q=Rs Q0=Ra Z=海拔=100米
    Tmax = 273.6 + Tmax
    Tmin = 273.6 + Tmin
    SRo = 0.75 * Ra
    RnL = 4.903 * 10e-9 * 0.25 * (Tmax ** 4 - Tmin ** 4) * (0.34 - 0.14 * ea ** 0.5) * (1.35 * SR / SRo - 0.35)
    return RnL


"""
净辐射计算公式
"""


def R_net(Q, RnL, a=0.23):
    Rs = (1 - a) * Q  # Q为天文辐射
    Rns = Rs - RnL  # Rnl净长波辐射
    return Rns


def e0(T):
    e = 0.6108 * (math.e ** ((17.27 * T / (T + 237.3))))
    return e


"""ET0为参考蒸散量，mm/day；
Rn为作物表面上的净辐射，MJ/（m2 day）；
G为土壤热通量，MJ/（m2 day）；
T为2米高处日平均气温，℃；
u2为2米高处的风速，m/s；
es为饱合水汽压，kPa；
ea为实际水汽压，kPa；
es-ea为饱和水汽压差，kPa；
∆为饱和水汽压曲线的斜率；
r为湿度计常数，kPa/℃。
"""


def PM_ET0(Tmax, Tmin, P, u2, now: dt.datetime):
    # Tmax、Tmin、Tmean为最高、最低、平均气温；Tdew为露点温度；P为本站气压;u2为2m风速;Rn为净辐射
    Tmean = 0.5 * (Tmax + Tmin)
    # 土壤热通量
    G = 0
    # 露点温度
    Tdew = 0
    # 饱和水汽压
    es = 0.5 * (e0(Tmax) + e0(Tmin))
    # 实际水汽压
    ea = e0(Tmin)
    # 饱和水汽压曲线斜率
    delta = 4098 * e0(Tmean) / ((Tmean + 237.3) ** 2)
    # 湿度计常数
    r = 0.0677  # 修正自https://www.sciencedirect.com/science/article/pii/S0378377409003436#aep-section-id16
    # ET0 = ( 0.408*delta*(Rn-G) + r*900*u2*(es-ea)/(Tmean+273) )/( delta + r*(1 + 0.34*u2) )

    # 天文辐射
    Ra = cal_Ra(now.year, now.month, now.day)
    # 入射太阳辐射量
    sr = SR(Tmax, Tmin, Ra)

    Rnl = R_net_long(Tmax, Tmin, ea, sr, Ra)

    Rns = 0.77 * sr

    Rn = Rns - Rnl

    ET0_1 = 0.408 * delta * (Rn - G)
    ET0_2 = r * 900 * u2 * (es - ea) / (Tmean + 273)
    ET0_3 = delta + r * (1 + 0.34 * u2)
    ET0 = (ET0_1 + ET0_2) / ET0_3

    return ET0


def grow_days(plant_d, predict_d):
    d1 = plant_d.date()
    d2 = predict_d.date()
    days = (d2 - d1).days
    return days


def Pm_E(Kc, E0):
    return round(Kc * E0, 2)


def sun_duration(sunrise, sunset):
    match1 = re.search(r'(\d{2}):(\d{2})', sunrise)
    if match1:
        h1 = match1.group(1)
        min1 = match1.group(2)
    match2 = re.search(r'(\d{2}):(\d{2})', sunset)
    if match2:
        h2 = match2.group(1)
        min2 = match2.group(2)
    hours = int((-int(h1) * 60 - int(min1) + int(h2) * 60 + int(min2) + 30) / 60)
    return hours


# 只能预测未来30天内的作物需水，没有时间更长的天气预报
def predict_e(kind, plant_d, begin_d, end_d, datalist):
    # 单位：mm
    if kind not in ["corn", "vegetable", "wheat", "peanut", "cotton"]:
        return "未知类型"
    if dt.datetime.now() > begin_d + dt.timedelta(days=1):
        return "日期错误，过去的日期不需要预测"
    if end_d > dt.datetime.now() + timedelta(days=30):
        return "日期错误, end_day请选择未来30天内的日期"
    if plant_d > begin_d:
        return "日期错误"
    if begin_d > end_d:
        return "日期错误"
    now = dt.datetime.now()
    days = grow_days(now, end_d)
    if len(datalist) < days:
        return "数据长度小于预测天数，请检查上传的数据"
    E = 0
    E_list = []
    with open('model2/data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    Kc_list = data["Kc"][kind]
    # Kc分界点
    date_split = [plant_d + timedelta(days=int(i)) for i in Kc_list]
    day_i = begin_d  # yyyy-mm-dd
    day_list = [plant_d + timedelta(days=i) for i in range(days)]
    kc_values = list(Kc_list.values())
    categories = pandas.cut(day_list, date_split).codes
    kc_for_days = [kc_values[i + 1] for i in categories]

    for i in range(days):
        data_i_list = list(filter(lambda x: str(x['fxDate']) == dt.datetime.strftime(day_i, "%Y-%m-%d"), datalist))
        if len(data_i_list) == 0:
            continue
        data_i = data_i_list[0]
        Tmax = int(data_i['tempMax'])  # 最高气温
        Tmin = int(data_i['tempMin'])  # 最低气温
        P = float(data_i['pressure']) * 0.1  # 气压
        u2 = float(data_i['windSpeedDay'])  # 风俗
        E0 = PM_ET0(Tmax, Tmin, P, u2, dt.datetime.now())
        Kc = kc_for_days[i]
        # 计算读取Kc
        E_i = Pm_E(Kc, E0)
        E += E_i
        obj = {
            "date": day_i.strftime("%Y-%m-%d"),
            "smi": E_i
        }
        E_list.append(obj)
        day_i = day_i + timedelta(days=1)  # 计算后一天
    return E_list


def request_smi_predict(plant_d, begin_d, end_d, kind="wheat"):
    """
    请求计算需水量， 只能通过未来的30d天气预报相对准确预测未来需水量
    :param plant_d: 种植日期
    :param begin_d: 需求开始日期
    :param end_d: 需求结束日期
    :param kind: 作物类型，枚举：【"wheat", "vegetable", "corn】
    :return: 返回每日需水量与总需水量的json
    """
    data = request_weather()['daily']
    res = predict_e(kind, plant_d, begin_d, end_d, data)
    return res


def request_smi_experiential(plant_d, begin_d, end_d, kind="wheat"):
    if begin_d >= end_d:
        return 0
    if kind not in ["corn", "vegetable", "wheat", "peanut", "cotton"]:
        return "未知类型"

    with open('model2/data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    Kc_list = data["Kc"][kind]
    days = grow_days(plant_d, end_d)
    # Kc分界点
    date_split = [plant_d + timedelta(days=int(i)) for i in Kc_list]
    day_i = begin_d.date()  # yyyy-mm-dd
    day_list = [plant_d + timedelta(days=i) for i in range(days)]
    kc_values = list(Kc_list.values())
    categories = pandas.cut(day_list, date_split).codes
    kc_for_days = [kc_values[i + 1] for i in categories]
    with open('model2/ave_e0.csv', 'r', encoding='utf-8') as f:
        df = pd.read_csv(f)

    plant_day = plant_d
    day_cursor = begin_d  # 从这一天开始计算
    end_day = end_d
    smi_list = []
    kc_index = (day_cursor - plant_day).days
    for i in range(len(kc_for_days)):
        if day_cursor >= end_day:
            break
        month_cursor = day_cursor.month
        day_c = day_cursor.day
        search_day_model = dt.datetime(2024, month_cursor, day_c)

        e0_from_file = float(df[pd.to_datetime(df['date']) == search_day_model]['E0_ave'])
        smi = {
            "date": day_cursor.strftime("%Y-%m-%d"),
            "smi": round(e0_from_file * kc_for_days[kc_index], 2),
        }
        smi_list.append(smi)
        day_cursor = day_cursor + timedelta(days=1)
        kc_index += 1

    return smi_list


def calculate_et0():
    return


if __name__ == '__main__':
    request_smi_predict("2025-7-1", "2025-7-4", "2025-7-13")
    res = request_smi_experiential("2025-7-1", "2025-7-4", "2026-7-13")
    print(res)
