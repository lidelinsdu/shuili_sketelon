import json
with open("../data/model2-response-2025-7-24---2026-7-23.json", 'r', encoding='utf-8') as f:
    data = json.load(f)
json_data = json.loads(data)
with open("../data/model2-response-2025-7-24---2026-7-23.json", 'w', encoding='utf-8') as f:
    json.dump(json_data, f, ensure_ascii=False, indent=4)