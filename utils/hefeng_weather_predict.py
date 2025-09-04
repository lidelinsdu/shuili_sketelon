import requests
import yaml
import utils.file_path_processor

def request_weather():
    with open("config/configuration_local.yaml", 'r', encoding='utf-8') as ymlfile:
        cfg = yaml.safe_load(ymlfile)
    hefeng = cfg['hefeng']
    api_key = hefeng['api-key']
    location = hefeng['location']  # 肥城
    latitude = hefeng['latitude']
    longitude = hefeng['longitude']
    api_host = 'mp4bj8ygm9.re.qweatherapi.com'
    api_name = '/v7/weather/30d'
    url = f'https://{api_host}/{api_name}?location={longitude},{latitude}&key={api_key}'
    res = requests.get(url)
    json_data = res.json()
    return json_data


if __name__ == '__main__':
    print(request_weather())
