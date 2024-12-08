from flask import Flask, request, render_template
import requests
from datetime import datetime

app = Flask(__name__)

API_KEY = 'U8k9RWeAo9PSaxVU8OgGpkWt3MRIGtRc'

def get_season():
    month = datetime.now().month
    if month in [12, 1, 2]:
        return "зима"
    elif month in [3, 4, 5]:
        return "весна"
    elif month in [6, 7, 8]:
        return "лето"
    else:
        return "осень"

#функция для классификации погоды на хорошую и плохую
def check_bad_weather(temperature, wind_speed, precipitation_probability):
    season = get_season()
    # Логика для зимы
    if season == "зима":
        if temperature < -10 or temperature > 5 or wind_speed > 30 or precipitation_probability > 50:
            return "Ой-ой, погода плохая"
    # Логика для весны
    elif season == "весна":
        if temperature < 0 or temperature > 25 or wind_speed > 40 or precipitation_probability > 60:
            return "Ой-ой, погода плохая"
    # Логика для лета
    elif season == "лето":
        if temperature < 15 or temperature > 35 or wind_speed > 50 or precipitation_probability > 70:
            return "Ой-ой, погода плохая"
    # Логика для осени
    elif season == "осень":
        if temperature < 0 or temperature > 20 or wind_speed > 40 or precipitation_probability > 60:
            return "Ой-ой, погода плохая"

    return "Погода — супер"

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/weather', methods=['POST'])
def weather():
    start_city = request.form.get('start_city')
    end_city = request.form.get('end_city')

    # получаем координаты для начального и конечного городов
    start_latitude, start_longitude, error_message = get_coordinates(start_city)
    if error_message:
        return render_template('result.html', weather_condition=error_message)

    end_latitude, end_longitude, error_message = get_coordinates(end_city)
    if error_message:
        return render_template('result.html', weather_condition=error_message)

    try:
        # Получаем погоду для начального города
        start_location_key = get_location_key(start_latitude, start_longitude)
        current_weather_start = get_current_weather(start_location_key)
        weather_parameters_start = extract_weather_parameters(current_weather_start)
        rain_probability_start = extract_rain_probability(get_forecast(start_location_key))
        weather_parameters_start['rain_probability_percent'] = rain_probability_start

        # Получаем погоду для конечного города
        end_location_key = get_location_key(end_latitude, end_longitude)
        current_weather_end = get_current_weather(end_location_key)
        weather_parameters_end = extract_weather_parameters(current_weather_end)
        rain_probability_end = extract_rain_probability(get_forecast(end_location_key))
        weather_parameters_end['rain_probability_percent'] = rain_probability_end

        # Оценка погодных условий
        result_start = check_bad_weather(
            weather_parameters_start['temperature_celsius'],
            weather_parameters_start['wind_speed_kph'],
            weather_parameters_start['rain_probability_percent']
        )
        result_end = check_bad_weather(
            weather_parameters_end['temperature_celsius'],
            weather_parameters_end['wind_speed_kph'],
            weather_parameters_end['rain_probability_percent']
        )

        # Проверяем, есть ли плохая погода в любом из городов
        if result_start == "Ой-ой, погода плохая" or result_end == "Ой-ой, погода плохая":
            weather_condition = "Ой-ой, погода плохая"
        else:
            weather_condition = "Погода — супер"

        return render_template('result.html',
                               weather_condition=weather_condition,
                               start_weather=weather_parameters_start,
                               end_weather=weather_parameters_end)

    except Exception as e:
        return render_template('result.html', weather_condition=f"Произошла ошибка: {str(e)}")

# функция для получения координат города
from requests.exceptions import ConnectionError

# функция для получения координат города
def get_coordinates(city_name):
    url = f'http://dataservice.accuweather.com/locations/v1/cities/search'
    params = {
        'apikey': API_KEY,
        'q': city_name,
        'language': 'ru-ru'
    }

    try:
        response = requests.get(url, params=params)
        if response.status_code != 200:
            return None, None, "Ошибка при получении координат: HTTP статус " + str(response.status_code)

        data = response.json()
        if not data:
            return None, None, "Нет данных о местоположении"

        # возвращаем первую найденную координату
        return data[0]['GeoPosition']['Latitude'], data[0]['GeoPosition']['Longitude'], None

    except ConnectionError:
        return None, None, "Ошибка подключения к серверу. Проверьте ваше интернет-соединение."
    except Exception as e:
        return None, None, f"Произошла ошибка: {str(e)}"


# функция для получения ключа местоположения по координатам
def get_location_key(latitude, longitude):
    url = 'http://dataservice.accuweather.com/locations/v1/cities/geoposition/search'
    params = {
        'apikey': API_KEY,
        'q': f'{latitude},{longitude}',
        'language': 'ru-ru'
    }
    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(f"Ошибка при получении данных о местоположении: {response.status_code}")
        return None

    data = response.json()
    if 'Key' not in data:
        print("Ошибка: 'Key' не найден в ответе от API")
        return None

    return data['Key']

def get_current_weather(location_key):
    url = f'http://dataservice.accuweather.com/currentconditions/v1/{location_key}'
    params = {
        'apikey': API_KEY,
        'language': 'ru-ru',
        'details': 'true'
    }
    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(f"Ошибка при получении данных о погоде: {response.status_code}")
        return None

    data = response.json()
    if not data:
        print("Ошибка: Нет данных о погоде")
        return None

    return data[0]  # Получаем первый элемент списка
def extract_weather_parameters(weather_data):
    try:
        temperature_celsius = weather_data['Temperature']['Metric']['Value']
        humidity_percent = weather_data['RelativeHumidity']
        wind_speed = weather_data['Wind']['Speed']['Metric']['Value']
    except KeyError as e:
        print(f"Ошибка извлечения данных: {e}")
        return None

    return {
        'temperature_celsius': temperature_celsius,
        'humidity_percent': humidity_percent,
        'wind_speed_kph': wind_speed
    }
def get_forecast(location_key):
    url = f'http://dataservice.accuweather.com/forecasts/v1/daily/1day/{location_key}'
    params = {
        'apikey': API_KEY,
        'language': 'ru-ru',
        'details': 'true',
        'metric': 'true'
    }
    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(f"Ошибка при получении прогноза погоды: {response.status_code}")
        return None

    data = response.json()
    if not data or 'DailyForecasts' not in data:
        print("Ошибка: Нет данных о прогнозе погоды")
        return None

    return data
def extract_rain_probability(forecast_data):
    try:
        rain_probability = forecast_data['DailyForecasts'][0]['Day']['PrecipitationProbability']
    except KeyError as e:
        print(f"Ошибка извлечения вероятности дождя: {e}")
        return 'Не доступно'

    return rain_probability

if __name__ == '__main__':
    app.run(debug=True)
