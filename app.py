from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator
from shared_code import weatherforecast, solar, ml
import pandas as pd
import json 
import pytz
from datetime import datetime

description = """
This API helps you optimizing your Solar energy by predicting. 🚀

### How ?

* **clearsky** -> returns 15min Power(Watts) of the day for maximal condition - clear sky.
* **forecast** -> returns 15min Power(Watts)  + weather for next 2 days.

### Format of your solar Installation

**Example:**

{
  "date": "10-13-2022",
  "location": {
    "lat": 51.0,
    "lng": 3.11
  },
  "altitude": 70,
  "tilt": 35,
  "azimuth": 170,
  "totalWattPeak": 7400,
  "wattInvertor": 5040,
  "timezone": "Europe/Brussels"
}
"""

class Location(BaseModel):
    lat: float = 51.0
    lng: float = 3.11

    @validator('lat')
    def validate_lat(cls, value):
        if not (-90 <= value <= 90):
            raise ValueError("latitude must be between -180 and +180")
        return value

    @validator('lng')
    def validate_lng(cls, value):
        if not (-180 <= value <= 180):
            raise ValueError("longitude must be between 0 and +90")
        return value

class Installation(BaseModel):
    date: str = "10-13-2022"
    location: Location
    altitude: int = 70
    tilt: int = 35
    azimuth: int = 170
    totalWattPeak: int = 7400
    wattInvertor: int = 5040
    timezone: str = "Europe/Brussels"

    @validator('date')
    def validate_date(cls, value):
        datetime.strptime(value, "%m-%d-%Y")
        return value

    @validator('altitude')
    def validate_altitude(cls, value):
        if not (0 <= value <= 5000):
            raise ValueError("altitude must be between 0 and 5000")
        return value

    @validator('tilt')
    def validate_tilt(cls, value):
        if not (0 <= value < 90):
            raise ValueError("tilt must be between 0 and 90")
        return value

    @validator('azimuth')
    def validate_azimuth(cls, value):
        if not (0 <= value < 360):
            raise ValueError("azimuth must be between 0 and 360")
        return value
    
    @validator('totalWattPeak')
    def validate_totalWattPeak(cls, value):
        if not (0 <= value < 20000):
            raise ValueError("totalWattPeak must be between 0 and 20000")
        return value
    
    @validator('wattInvertor')
    def validate_wattInvertor(cls, value):
        if not (0 <= value < 10000):
            raise ValueError("wattInvertor must be between 0 and 10000")
        return value
    
    @validator('timezone')
    def validate_timezone(cls, value):
        if not (value in pytz.all_timezones):
            raise ValueError("the provided timezone seems not correct.")
        return value



app = FastAPI(
    title="solar-forecast-api",
    description=description,
    version="0.0.1",
    contact={
        "name": "Peter Tribout",
        "url": "https://github.com/tribp",
    },
    license_info={
        "name": "GNU General Public License v3.0",
        "url": "https://www.gnu.org/licenses/gpl-3.0.en.html",
    },

)


@app.get("/")
async def root():
    return {"message": "Hello wizzkid!!"}

@app.post("/forecast")
async def calc_forecast(installation: Installation):
    inst = installation.dict()

    # list of dicts : get weather forecast + day_of_year => After this we only need the clearSky power
    # OpnemweatherMap: dt : (date= epoch in sec-10digits)
    forecast = weatherforecast.getOpenWeatherData(inst.get("location"))
    forecast_15min = weatherforecast.createForecast_15min(forecast)
    forecast_15min_df = pd.DataFrame(forecast_15min)

    # Determine startHour and stopHour
    startEpochHour, stopEpochHour = forecast[0]["dt"], forecast[-1]["dt"]

    # Calculate ClearSky and return dataFrame (date= epoch in sec-10digits)
    clear_sky_df = pd.DataFrame()
    clear_sky_df = solar.getClearSky(
                inst, startEpochHour=startEpochHour, stopEpochHour=stopEpochHour
        )

    # Combine hourly weatherforecast with 15min clearSky
    dataSet = pd.DataFrame()
    dataSet = pd.concat([clear_sky_df, forecast_15min_df], axis=1)
    # logging.info(f"Succesfull combined dataSet:{dataSet.info()}")

    
    # Get ML prediction
    Final = pd.DataFrame()
    Final = ml.enrichDataFrameWithPrediction(dataSet)

    msg_dict = Final.to_dict("records")

    return msg_dict

@app.post("/clearsky")
async def calc_clearsky(installation: Installation):
    inst = installation.dict()

    clear_sky_df = pd.DataFrame()
    clear_sky_df = solar.getClearSky(inst)
    # convert to dict and than to string
    msg_dict = clear_sky_df.to_dict("records")

    return msg_dict