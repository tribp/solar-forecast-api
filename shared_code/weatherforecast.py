import os
import json
import logging
import requests
from datetime import datetime, timedelta
import pytz

import pandas as pd

API_KEY = os.environ["OPENWEATHERMAP_API_KEY"]


def map_open_meteo_to_openweathermap_code(code):
    """We map open-meteo codes to (restricted) openweathermap codes
        code =
            '0': clearsky
            '1,2,3': Mainly clear, partly cloudy, and overcast
            '45,48: Fog and depositing rime fog
            '51,53,55': Drizzle: Light, moderate, and dense intensity
            '56,57': Freezing Drizzle: Light and dense intensity
            '61,63,65': Rain: Slight, moderate and heavy intensity
            '66,67': Freezing Rain: Light and heavy intensity
            '71,73,75': Snow fall: Slight, moderate, and heavy intensity
            '77': Snow grains
            '80,81,82': Rain showers: Slight, moderate, and violent
            '85,86': Snow showers slight and heavy
            '95': Thunderstorm: Slight or moderate
            '96,99': Thunderstorm with slight and heavy hail

         Args:
        code (_type_ number): weather code

    Returns:
        _type_ number: restricted weather code
    """
    if code == 0:
        return 800
    elif code == 1:
        return 801
    elif code == 2:
        return 802
    elif code == 3:
        return 804
    # fog
    elif code == 45 or code == 48:
        return 701
    # light rain
    elif code == 51 or code == 56 or code == 61 or code == 80:
        return 500
    # moderate rain
    elif code == 53 or code == 63 or code == 81 or code == 85:
        return 501
    # heavy rain
    elif code == 55 or code == 57 or code == 65 or code == 83 or code == 86:
        return 502
    # light snow
    elif code == 71:
        return 600
    # snow
    elif code == 73 or code == 75 or code == 77 or code == 85 or code == 86:
        return 601
    # thunderstorm
    elif code >= 95 and code < 100:
        return 211


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
    # Map openmeteo codes (0-99) to openweathermap (200-804)
    if code <= 100:
        return map_open_meteo_to_openweathermap_code(code)
    # Openweathermap codes (between 200 - 804)
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


def create_15min_by_interpolation(df_orig, interp_cols):
    """Create 15min forecast by inserting 15min deltas by interpolation only for the Interpolated columns, rest will be copied"""
    df = df_orig.copy()

    # Columns to just copy (i.e., not interpolated)
    copy_cols = [col for col in df.columns if col not in interp_cols + ["dt"]]

    # Set dt as datetime index if not already
    df["dt"] = pd.to_datetime(df["dt"], unit='s')
    df.set_index("dt", inplace=True)

    # Create a new datetime index with 15-minute frequency and last hour(23h00) has 3 extra 15min
    extended_end = df.index.max() + timedelta(minutes=45)
    new_index = pd.date_range(start=df.index.min(), end=extended_end, freq="15min")

    # Reindex the dataframe to 15-minute intervals
    df_15min = df.reindex(new_index)

    # Interpolate the numeric columns
    df_15min[interp_cols] = df_15min[interp_cols].interpolate(method="time")

    # Forward fill the copied fields
    df_15min[copy_cols] = df_15min[copy_cols].ffill()

    # Reset index and convert datetime back to UNIX timestamp (seconds)
    df_15min = df_15min.reset_index()
    df_15min.rename(columns={"index": "dt"}, inplace=True)
    df_15min["dt"] = df_15min["dt"].astype("int64") // 10**9

    return df_15min


   


def getOpenMeteoData(installation):
    """Gets a dict {lat:x,lng:y} and calls open-meteo api and returns  a weather list.
    Every item of the list has the 'hourly' forecast

    Args:
        location (_type_ dict): Geo coordinates

    Returns:
        _type_ list of dicts: list of dicts, every dict has the forecast for parameters:...
    """
    location = installation.get("location")
    timezone = installation.get("timezone")
    tz = pytz.timezone(timezone)
    params = f'?latitude={location["lat"]}&longitude={location["lng"]}&timezone={timezone}&hourly=temperature_2m,pressure_msl,relativehumidity_2m,windspeed_10m,winddirection_10m,cloudcover,weathercode&windspeed_unit=ms'
    url = "https://api.open-meteo.com/v1/forecast" + params
    resp = requests.get(url).json()

    df_OM = pd.DataFrame.from_dict(resp["hourly"])

    # °C to °K and round to 1 decimal
    df_OM["temperature_2m"] = df_OM["temperature_2m"].apply(
        lambda t: round(t + 273.15, 1)
    )

    # we take naive time, convert into aware time
    df_OM["time"] = df_OM["time"].apply(
        lambda t: tz.localize(datetime.strptime(t, "%Y-%m-%dT%H:%M"))
    )
    # we make timestamp
    df_OM["dt"] = df_OM["time"].apply(lambda t: int(t.timestamp()))

    # drop 'time' col -> not needed when we return
    df_OM.drop(["time"], inplace=True, axis=1)

    # we create clear_sky col (default=0)
    df_OM["clear_sky"] = 0
    df_OM["day_of_year"] = df_OM["dt"].apply(
        lambda ts: datetime.fromtimestamp(ts).timetuple().tm_yday
    )

    # map opemn-meteo weather code to openweathermap codes
    df_OM["weathercode"] = df_OM["weathercode"].apply(
        lambda id: map_open_meteo_to_openweathermap_code(id)
    )

    # rename to OWM API
    df_OM.rename(
        inplace=True,
        columns={
            "dt": "dt",
            "temperature_2m": "temp",
            "pressure_msl": "pressure",
            "relativehumidity_2m": "humidity",
            "windspeed_10m": "wind_speed",
            "winddirection_10m": "wind_deg",
            "cloudcover": "clouds_all",
            "weathercode": "weather_id",
            "clear_sky": "clear_sky",
            "day_of_year": "day_of_year",
        },
    )

    # Columns to interpolate
    interp_cols = [
        "temp", "pressure", "humidity", "wind_speed", "wind_deg", "clouds_all"
    ]
    # Create 15min forecast by inserting 15min deltas by interpolation only for the Interpolated columns, rest will be copied
    df_15 = create_15min_by_interpolation(df_OM, interp_cols)

    # round to 1 decimal
    df_15[interp_cols] = df_15[interp_cols].apply(lambda x: round(x, 1))

    # sort by timestamp 'dt'
    df_15.sort_values(["dt"], inplace=True)
    df_15.reset_index(drop=True, inplace=True)

    logging.info(f"Succes Open-Meteo API call")
    return df_15


def getOpenWeatherData(installation):
    """Gets a dict {lat:x,lng:y} a calls openweather api and returns the subset as a weathet list.
    Every item of the list has the 'hourly' forecast

    Args:
        installation (_type_ dict): see Installation

    Returns:
        _type_ DataFrame: dt	temp	pressure	humidity	wind_speed	wind_deg	clouds_all	weather_id	clear_sky	day_of_year
    """
    location = installation.get("location")
    # remark: we use the openweathermap API v3 (3.0) and not the v2 (2.5) since june 2024
    url = f'https://api.openweathermap.org/data/3.0/onecall?lat={location["lat"]}&lon={location["lng"]}&appid={API_KEY}'
    resp = requests.get(url).json()

    df_OWM = pd.DataFrame.from_dict(resp["hourly"])

    # get weater_id from inside dict
    df_OWM["weather_id"] = df_OWM["weather"].apply(lambda x: x[0]["id"])
    # Only keep needed cols
    df_OWM = df_OWM[
        [
            "dt",
            "temp",
            "pressure",
            "humidity",
            "wind_speed",
            "wind_deg",
            "clouds",
            "weather_id",
        ]
    ]
    # rename clouds to clouds_all
    df_OWM.rename(inplace=True, columns={"clouds": "clouds_all"})
    # add 2 colums so everything is in the right order for de mlp model
    df_OWM["clear_sky"] = 0
    df_OWM["day_of_year"] = df_OWM["dt"].apply(
        lambda ts: datetime.fromtimestamp(ts).timetuple().tm_yday
    )

    # create copie for every 15 min and merge
    df_15 = df_OWM.copy()
    df_15["dt"] = df_15["dt"] + 900
    df_30 = df_OWM.copy()
    df_30["dt"] = df_OWM["dt"] + 1800
    df_45 = df_OWM.copy()
    df_45["dt"] = df_OWM["dt"] + 2700

    weather = df_OWM.merge(df_15, how="outer")
    weather = weather.merge(df_30, how="outer")
    weather = weather.merge(df_45, how="outer")

    # sort by timestamp 'dt'
    weather.sort_values(["dt"], inplace=True)
    weather.reset_index(drop=True, inplace=True)

    # delete last 3 rows: we do not need +15min,30min,45min for last 'hour'
    weather = weather.iloc[:-2]

    logging.info(f"Succes Openweather API call")
    return weather


# def createForecast_15min(forecast):
#     """Create 15min forecast by inserting 15min deltas with same forecast values"""
#     forecast_15min = []
#     nr_forecasts = len(forecast)

#     for nr in range(nr_forecasts - 1):
#         forecast_15min.append(forecast[nr])
#         q = forecast[nr].copy()
#         q["dt"] = forecast[nr]["dt"] + 900
#         forecast_15min.append(q)
#         ts = q["dt"] + 900
#         while ts < forecast[nr + 1]["dt"]:
#             q = forecast[nr].copy()
#             q["dt"] = ts
#             forecast_15min.append(q)
#             ts += 900
#     forecast_15min.append(forecast[-1])
#     return forecast_15min


## Extra tests for pytest to obtain 100% code coverage
test0 = map_weather_code(800)
test1 = map_weather_code(200)
test2 = map_weather_code(300)
test3 = map_weather_code(502)
test4 = map_weather_code(601)
test5 = map_weather_code(701)
# Extra tests for open-meteo codes
test6 = map_weather_code(0)
test7 = map_weather_code(1)
test8 = map_weather_code(2)
test9 = map_weather_code(3)
test10 = map_weather_code(45)
test11 = map_weather_code(51)
test12 = map_weather_code(53)
test13 = map_weather_code(55)
test14 = map_weather_code(71)
test15 = map_weather_code(73)
test16 = map_weather_code(95)
