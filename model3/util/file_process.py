# 处理测试文件
import json

with open("../data/water_requirement_example.json", 'r', encoding='utf-8') as f:
    water_requirement_json = json.load(f)

result = []
for i in water_requirement_json:
    area_name = list(i.keys())[0]
    water_demand_list = i[area_name]
    new_list = [{"date": key, "smi": value * 5} for key, value in water_demand_list.items()]
    result.append({
        'area_name': area_name,
        'water_demand': new_list
    })

with open("../data/water_demand.json", 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=4)
