import logging
import json
from operator import itemgetter
import pandas as pd
import numpy as np
import pvlib
from pvlib import clearsky, atmosphere, solarposition, irradiance
from pvlib.location import Location
from datetime import datetime


def get_irradiance(site_location, date, tilt, surface_azimuth, **kwargs):
    """Returns the 'Clear Sky Power (GHI and POI at every 15min interval for a given day '
        Remark : all timestamps are refered GMT+0 and we need it to convert in frontend to timezone
    Args:
        site_location (pvlib Location object): (latitude, longitude, tz='UTC', altitude=0, name=None)
        date (string - 'MM-DD-YYYY'): A day of the year
        tilt (integer): Inclination of the installation (deg °) typical roof = 35°
        surface_azimuth (integer): Orientation of solar installation (deg °) eg 180°=south

    Returns:
        pandas dataframe: {'GHI': clearsky['ghi'], 'POA': POA_irradiance['poa_global']}
    """

    # Creates one day's worth of 15 min intervals
    if kwargs:
        # return 48h x 4(15min) + 1 timestamps from startEpochHour upto and ending stopEpochHour
        start = datetime.fromtimestamp(kwargs["startEpochHour"])
        stop = datetime.fromtimestamp(kwargs["stopEpochHour"])
        times = pd.date_range(start=start, end=stop, freq="15min", tz=site_location.tz)
    else:
        # return 24h x 4(15min) timstamps for one complete day
        times = pd.date_range(date, freq="15min", periods=4 * 24, tz=site_location.tz)

    # Generate clearsky data using the Ineichen model, which is the default
    # The get_clearsky method returns a dataframe with values for GHI, DNI,
    # and DHI
    clearsky = site_location.get_clearsky(times)
    # Get solar azimuth and zenith to pass to the transposition function
    solar_position = site_location.get_solarposition(times=times)
    # Use the get_total_irradiance function to transpose the GHI to POA
    POA_irradiance = irradiance.get_total_irradiance(
        surface_tilt=tilt,
        surface_azimuth=surface_azimuth,
        dni=clearsky["dni"],
        ghi=clearsky["ghi"],
        dhi=clearsky["dhi"],
        solar_zenith=solar_position["apparent_zenith"],
        solar_azimuth=solar_position["azimuth"],
    )
    # Return DataFrame with only GHI and POA
    return pd.DataFrame({"POA": POA_irradiance["poa_global"]})


def getClearSky(body, **kwargs):
    """ " Calculates for a certain date and PV installation parameters the 'Clear Sky' power in Watts for every 15 of that day.

    Args:
        body (dict):
            date (string): "dd-MM-yyy"
            location (_type_): {lat:x,lng:y}
            altitude (int): altitude
            tilt (int): inclination of PV panels to the earth's surface
            azimuth (int): 'compas' deg of installation
            totalWattPeak (int): Total Peak power of installation: this is n x solarpanel power
            wattInvertor (int): max power of invertor
            timezone (string): official IANA timezone
        **kwargs:
            startEpochHour (int): sec
            stopEpochHour (int): sec

    Returns:
        pandas dataframe: 96 x ( index + 'date'(int32) + 'P_invertor'(int16) )
    """

    (
        dateEU,
        location,
        altitude,
        tilt,
        azimuth,
        P_Installed,
        P_Invertor,
        timezone,
    ) = itemgetter(
        "date",
        "location",
        "altitude",
        "tilt",
        "azimuth",
        "totalWattPeak",
        "wattInvertor",
        "timezone",
    )(
        body
    )

    # re-format date from dd-MM-yyyy to MM-dd-yyyy
    date = dateEU[3:5] + "-" + dateEU[0:2] + "-" + dateEU[6:]

    site = Location(location["lat"], location["lng"], timezone, altitude, "MySite")

    if kwargs:
        irradiance = get_irradiance(
            site,
            date,
            tilt,
            azimuth,
            startEpochHour=kwargs["startEpochHour"],
            stopEpochHour=kwargs["stopEpochHour"],
        )
    else:
        irradiance = get_irradiance(site, date, tilt, azimuth)

    # we assume max sun power =+/- 1000 Watt/m2 (913) and have a installation of peak 7480 Watt so we multiply by 7.48
    cf = 0.97
    P_max_m2 = 913
    P_peak = P_Installed / P_max_m2
    irradiance["clear_sky"] = cf * P_peak * irradiance["POA"]

    # we clip the produced powe to the max of the inverter (5040 Watt in this case)
    irradiance["clear_sky"] = irradiance["clear_sky"].apply(
        lambda x: P_Invertor if x > P_Invertor else x
    )
    # remove POA
    irradiance.drop(["POA"], inplace=True, axis=1)

    # reset index: before date was index -> this wil create new column + we rename it
    irradiance = irradiance.reset_index().rename(columns={"index": "dt"})

    # convert date from datetime type to iso-string -> needed becaus key in dict must be native python type
    # irradiance["date"] = irradiance["date"].map(lambda x: x.isoformat())

    # convert date from datetime type to epoch secs (int64)
    irradiance["dt"] = irradiance["dt"].map(lambda x: x.timestamp())

    # round power to int
    irradiance = irradiance.astype({"clear_sky": np.int16, "dt": np.int32})

    # we return a pandas.DataFrame
    return irradiance


# def addForecastToClearSky_df(forecast, clearSky_df):
#     """ClearSky has every 15min power values, forecast has "hourly" weather predictions.
#     We will combine both into a dataframe for every 15min.
#     Note that we gave all xxh:00, xxh:15, xxh:30,xxh:45 identical weather parameter predictions

#     Args:
#         forecast (dict): weather parameters for every hour of the specific day
#         clearSky_df (pandas dataFrame): every 15min epoch timestamp(sec) with calculated Clear Sky power in Watt

#     Returns:
#         dataframe: 96 (every 15min of the day)
#             date: epoch (sec)
#             clear_sky: Watt (Calculated Power by clear sky conditions)
#             temp: °K
#             pressure: mbar
#             humidity: %
#             wind_speed: m/s
#             wind_deg: deg
#             clouds_all: % cloudcoverage
#             weather_id: see table
#             day_of_year: 1-366
#     """
#     dataSet = pd.DataFrame(
#         columns=[
#             "temp",
#             "pressure",
#             "humidity",
#             "wind_speed",
#             "wind_deg",
#             "clouds_all",
#             "weather_id",
#             "day_of_year",
#         ],
#         dtype=np.int16,
#     )
#     clearSky = pd.concat([clearSky_df, dataSet])
#     clearSky = clearSky.astype({"date": np.int32})
#     for point in forecast:
#         # search corresponding "hour" timestamp and give the 3 next 15min the same weather data
#         index = clearSky.loc[clearSky["date"] == point["dt"]].index[0]
#         clearSky.loc[index, 2:10] = [
#             point["temp"],
#             point["pressure"],
#             point["humidity"],
#             point["wind_speed"],
#             point["wind_deg"],
#             point["clouds_all"],
#             point["weather_id"],
#             point["day_of_year"],
#         ]

#     logging.info("Success addForeCastToClearSky")

#     return clearSky
