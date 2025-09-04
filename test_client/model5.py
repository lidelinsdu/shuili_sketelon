import json

import requests

json_str = """
[{"red_dir": "model5/upload_files/DJI_20230215103951_0003_MS_R.TIF", "nir_dir":"model5/upload_files/DJI_20230215103951_0003_MS_NIR.TIF"},{"red_dir": "model5/upload_files/DJI_20230215103951_0003_MS_R.TIF", "nir_dir":"model5/upload_files/DJI_20230215103951_0003_MS_NIR.TIF"}]
"""

data = json.loads(json_str)
print(requests.get("http://localhost:8081/model5/dynamic_smi",
                   json={
                       "file_list": data,
                   }
                   ).content)
print("ok")

# with open('../model1/data/model1_response_2025-7-1---2025-6-30.json', 'r', encoding='utf-8') as f:
#     p_list = json.load(f)['forecast_inflow']
#
# param = {
#     "span": "year",
#     "history_avg": 50,
#     "precip_list": p_list,
# }
# url = "http://nas.jnaw.top:5009/model5/get_rain_avg_lap_rate"
# print(requests.get(url, json=param).content)
# print("ok")
