import json
import math
import datetime as dt
import re
from datetime import timedelta
import pandas
import requests

param = {
    'location': '116.46,35.57'
}
headers = {
    'X-QW-Api-Key': '1647396dc7214c62992c61940f9e64dd'
}


def get_weather_prediction(days):
    res = requests.get(f'https://devapi.qweather.com/v7/weather/{days}', params=param, headers=headers)
    return res.json()


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


def PM_ET0(Tmax, Tmin, P, u2, N):
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

    # 当前时间
    now = dt.datetime.now()
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
    d1 = dt.datetime.strptime(plant_d, "%Y-%m-%d").date()
    d2 = dt.datetime.strptime(predict_d, "%Y-%m-%d").date()
    days = (d2 - d1).days
    return days


def Pm_E(Kc, E0):
    return Kc * E0


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
    if dt.datetime.now() > dt.datetime.strptime(begin_d, "%Y-%m-%d"):
        return "日期错误，过去的日期不需要预测"
    if dt.datetime.strptime(end_d, "%Y-%m-%d") > dt.datetime.now() + timedelta(days=30):
        return "日期错误, end_day请选择未来30天内的日期"
    if dt.datetime.strptime(plant_d, "%Y-%m-%d") > dt.datetime.strptime(begin_d, "%Y-%m-%d"):
        return "日期错误"
    if dt.datetime.strptime(begin_d, "%Y-%m-%d") > dt.datetime.strptime(end_d, "%Y-%m-%d"):
        return "日期错误"
    kind_list = ["corn", "wheat", "vegetable"]
    if kind not in kind_list:
        return f"作物种类错误，只能选择{kind_list}"
    days = grow_days(plant_d, end_d)
    if len(datalist) < days:
        return "数据长度小于预测天数，请检查上传的数据"
    E = 0
    E_list = []
    with open('data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    Kc_list = data["Kc"][kind]
    # Kc分界点
    date_split = [dt.datetime.strptime(plant_d, "%Y-%m-%d") + timedelta(days=int(i)) for i in Kc_list]
    day_i = dt.datetime.strptime(begin_d, "%Y-%m-%d").date()  # yyyy-mm-dd
    day_list = [dt.datetime.strptime(plant_d, "%Y-%m-%d") + timedelta(days=i) for i in range(days)]
    kc_values = list(Kc_list.values())
    categories = pandas.cut(day_list, date_split).codes
    kc_for_days = [kc_values[i + 1] for i in categories]

    for i in range(days):
        data_i_list = list(filter(lambda x: str(x['fxDate']) == str(day_i), datalist))
        if len(data_i_list) == 0:
            continue
        data_i = data_i_list[0]
        Tmax = int(data_i['tempMax'])
        Tmin = int(data_i['tempMin'])
        sunrise = data_i['sunrise']
        sunset = data_i['sunset']
        sunduration = sun_duration(sunrise, sunset)
        P = float(data_i['pressure']) * 0.1
        u2 = float(data_i['windSpeedDay'])
        E0 = PM_ET0(Tmax, Tmin, P, u2, sunduration)
        Kc = kc_for_days[i]
        # 计算读取Kc
        E_i = Pm_E(Kc, E0)
        E += E_i
        obj = {
            "date": day_i.strftime("%Y-%m-%d"),
            "E": E_i
        }
        E_list.append(obj)
        day_i = day_i + timedelta(days=1)  # 计算后一天
    return {
        "E_list": E_list,
        "ALL_E": E
    }


def request_E(plant_d, begin_d, end_d, kind="wheat"):
    data = get_weather_prediction("30d")['daily']
    res = predict_e(kind, plant_d, begin_d, end_d, data)
    print(json.dumps(res))


if __name__ == '__main__':
    request_E("2025-6-14", "2025-6-25", "2025-7-13")
