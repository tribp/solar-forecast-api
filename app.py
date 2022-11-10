from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from shared_code import weatherforecast, solar, ml
import pandas as pd
import json 

description = """
This API helps you optimizing your Solar energy by predicting. 🚀

### How ?

* **clearsky** -> returns 15min Power(Watts) of the day for maximal condition - clear sky.
* **forecast** -> returns 15min Power(Watts)  + weather for next 2 days.

### Format of your solar Installation

**Example:**

{
  "date": "10-09-2022",
  "location": {
    "lat": 51,
    "lng": 3.11
  },
  "altitude": 70,
  "tilt": 35,
  "azimuth": 180,
  "totalWattPeak": 7400,
  "wattInvertor": 5040,
  "timezone": "Europe/Brussels"
}
"""

class Location(BaseModel):
    lat: float
    lng: float

class Installation(BaseModel):
    date: str
    location: Location
    altitude: int
    tilt: int
    azimuth: int
    totalWattPeak: int
    wattInvertor: int
    timezone: str



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