import os
import json
import logging
import requests
from datetime import datetime

API_KEY = os.environ["OPENWEATHERMAP_API_KEY"]


def map_weather_code(code):
    """We resitrict number of atmosfpheric conditions to:
            weather_type = {
            '211': 'thunderstorm',
            '500': 'light rain',
            '501': 'moderate rain',
            '502': 'heavy rain',
            '600': 'light snow',
            '601': 'snow',
            '701': 'fog',
            '800': 'clear sky',
            '801': 'few clouds',
            '802': 'scattered clouds',
            '803': 'broken clouds',
            '804': 'overcast clouds'
        }

    Args:
        code (_type_ number): weather code

    Returns:
        _type_ number: restricted weather code
    """
    if code >= 200 and code < 300:
        # Thunderstorm
        return 211
    elif code >= 300 and code <= 500:
        # Drizzle -> light rain
        return 500
    elif code >= 502 and code <= 531:
        # Heavy Rain
        return 502
    elif code >= 601 and code <= 622:
        # Snow
        return 601
    elif code >= 701 and code <= 781:
        # Fog
        return 601
    else:
        return code


def getOpenWeatherData(location):
    """Gets a dict {lat:x,lng:y} a calls openweather api and returns the subset as a weathet list.
    Every item of the list has the 'hourly' forecast

    Args:
        location (_type_ dict): Geo coordinates

    Returns:
        _type_ list of dicts: list of dicts, every dict has the forecast for parameters:...
    """
    url = f'https://api.openweathermap.org/data/2.5/onecall?lat={location["lat"]}&lon={location["lng"]}&appid={API_KEY}'
    resp = requests.get(url).json()
    weather = []

    day_of_year = datetime.fromtimestamp(resp["current"]["dt"]).timetuple().tm_yday

    hourlyForecast = resp["hourly"]

    for item in hourlyForecast:
        weather.append(
            {
                "dt": item["dt"],
                "temp": item["temp"],
                "pressure": item["pressure"],
                "humidity": item["humidity"],
                "wind_speed": item["wind_speed"],
                "wind_deg": item["wind_deg"],
                "clouds_all": item["clouds"],
                "weather_id": map_weather_code(item["weather"][0]["id"]),
                "day_of_year": day_of_year,
            }
        )

    logging.info(f"Succes Openweather API call:{day_of_year}")
    return weather


def createForecast_15min(forecast):
    """Create 15min forecast by copying every hourly to the 3 quarters"""
    forecast_15min = []
    for prediction in forecast[:-1]:
        q1, q2, q3 = prediction.copy(), prediction.copy(), prediction.copy()
        q1["dt"] = prediction["dt"] + 900
        q2["dt"] = prediction["dt"] + 1800
        q3["dt"] = prediction["dt"] + 2700
        forecast_15min.extend([prediction, q1, q2, q3])
    forecast_15min.append(forecast[-1])
    return forecast_15min
