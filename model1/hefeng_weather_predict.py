import json

import requests

def request_weather():
    api_key='1647396dc7214c62992c61940f9e64dd'
    headers = {
        'X-QW-Api_Key': api_key
    }
    location = 101120804 # 肥城

    api_host='mp4bj8ygm9.re.qweatherapi.com'
    api_name='/v7/weather/30d'
    url = f'https://{api_host}/{api_name}?location={location}&key={api_key}'
    res = requests.get(url)
    json_data = json.loads(res.content)
    list = [{"date": i["fxDate"], "precip": i["precip"]} for i in json_data["daily"]]
    return list


if __name__=='__main__':
    print(request_weather())