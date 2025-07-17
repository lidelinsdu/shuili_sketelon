import requests
import yaml




def request_weather():
    with open("config/configuration.yaml", 'r') as ymlfile:
        cfg = yaml.safe_load(ymlfile)
    hefeng = cfg['hefeng']
    api_key = hefeng['api-key']
    location = hefeng['location']  # 肥城

    api_host = 'mp4bj8ygm9.re.qweatherapi.com'
    api_name = '/v7/weather/30d'
    url = f'https://{api_host}/{api_name}?location={location}&key={api_key}'
    res = requests.get(url)
    json_data = res.json()
    return json_data


if __name__ == '__main__':
    print(request_weather())
