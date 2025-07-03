import csv
import os
import shutil
import pandas as pd

dir_name = "D:\\weather_data\\tar\\"
target_dir = "D:\\weather_data\\history_data\\"
# os.mkdir(target_dir)
china_range_long = [116, 118]
china_range_lat = [35, 37]
target = "YANZHOU, CH"
for i in range(2009, 2024):
    for path, _, files in os.walk(dir_name + str(i)):
        for filename in files:
            fp = os.path.join(path, filename)
            data = pd.read_csv(fp)
            name = data['NAME']
            country = name[0]
            if country == target:
                shutil.copy(fp, target_dir+str(i)+".csv")
                print(i)

