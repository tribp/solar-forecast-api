from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, validator
from shared_code import weatherforecast, solar, ml
import pandas as pd
import json
import pytz
from datetime import datetime
import uvicorn

description = """
This API helps you optimizing your Solar energy by predicting. 🚀

### How ?

* **clearsky** -> returns 15min Power(Watts) of the day for maximal condition - clear sky.
* **forecast** -> returns 15min Power(Watts)  + weather for next 7 days.

**Remark:** 

* **clearsky**: works for any date or location on the planet.
* **forecast**: will only return data for the next 7d (or 48h). Obviously not for a "date" in the past or further in the future.

### Format of your solar Installation

**Example:**

{
  "date": "31-03-2022",
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

    @validator("lat")
    def validate_lat(cls, value):
        if not (-90 <= value <= 90):
            raise ValueError("latitude must be between -180 and +180")
        return value

    @validator("lng")
    def validate_lng(cls, value):
        if not (-180 <= value <= 180):
            raise ValueError("longitude must be between 0 and +90")
        return value


now = datetime.now()
now_string = now.strftime("%d-%m-%Y")


class Installation(BaseModel):
    date: str = now_string
    location: Location
    altitude: int = 70
    tilt: int = 44
    azimuth: int = 170
    totalWattPeak: int = 7400
    wattInvertor: int = 5040
    timezone: str = "Europe/Brussels"

    @validator("date")
    def validate_date(cls, value):
        try:
            d = datetime.strptime(value, "%d-%m-%Y")
        except:
            raise ValueError("date must be format: dd-MM-YYYY")
        return value

    @validator("altitude")
    def validate_altitude(cls, value):
        if not (0 <= value <= 5000):
            raise ValueError("altitude must be between 0 and 5000")
        return value

    @validator("tilt")
    def validate_tilt(cls, value):
        if not (0 <= value < 90):
            raise ValueError("tilt must be between 0 and 90")
        return value

    @validator("azimuth")
    def validate_azimuth(cls, value):
        if not (0 <= value < 360):
            raise ValueError("azimuth must be between 0 and 360")
        return value

    @validator("totalWattPeak")
    def validate_totalWattPeak(cls, value):
        if not (0 <= value < 20000):
            raise ValueError("totalWattPeak must be between 0 and 20000")
        return value

    @validator("wattInvertor")
    def validate_wattInvertor(cls, value):
        if not (0 <= value <= 10000):
            raise ValueError("wattInvertor must be between 0 and 10000")
        return value

    @validator("timezone")
    def validate_timezone(cls, value):
        if not (value in pytz.all_timezones):
            raise ValueError("the provided timezone seems not correct.")
        return value


app = FastAPI(
    title="solar-forecast-api",
    description=description,
    version="0.0.2",
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
    # Redirect the root to the Swagger doc page
    redirect_url = "/docs"
    return RedirectResponse(redirect_url, status_code=303)


@app.post("/forecast")
async def calc_forecast(installation: Installation):
    inst = installation.dict()

    # list of dicts : get weather forecast + day_of_year => After this we only need the clearSky power
    # OpnemweatherMap: dt : (date= epoch in sec-10digits)

    # depending on query param: ?provider='...' in POST
    # We only support openmeteo anymore since openweathermap is not free anymore
    provider = "openmeteo"

    if provider == "openweathermap":
        forecast_15min_df = weatherforecast.getOpenWeatherData(inst)
    elif provider == "openmeteo":
        forecast_15min_df = weatherforecast.getOpenMeteoData(inst)

    # Determine startHour and stopHour
    startEpochHour, stopEpochHour = (
        forecast_15min_df["dt"].iloc[0],
        forecast_15min_df["dt"].iloc[-1],
    )

    # Calculate ClearSky and return dataFrame (date= epoch in sec-10digits)
    clear_sky_df = pd.DataFrame()
    clear_sky_df = solar.getClearSky(
        inst, startEpochHour=startEpochHour, stopEpochHour=stopEpochHour
    )

    # fill in 'clearSky' in the provided col (default val=0)
    forecast_15min_df["clear_sky"] = clear_sky_df["clear_sky"]
    # logging.info(f"Succesfull combined dataSet:{dataSet.info()}")

    # Get ML prediction
    Final = pd.DataFrame()
    Final = ml.enrichDataFrameWithPrediction(forecast_15min_df)

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


if __name__ == "__main__":
    uvicorn.run(app, port=8080, host="0.0.0.0")
