
import logging
import pandas as pd
import numpy as np
import pickle
import sklearn

myModel_file = open("solar_mlp_model.pkl", "rb")
mlp = pickle.load(myModel_file)

# helper function clips positive Power to zero before sunrise and after sunset
def eliminate_power_outside_sunrise_sunset(row):
    Power = row["P_predicted"]
    if row["clear_sky"] == 0 or row["P_predicted"] < 0:
        Power = 0
    return int(Power)


def enrichDataFrameWithPrediction(dSet):
    # dSet: date/clear_sky/dt/temp/pressure/humidity/wind_speed/wind_deg/clouds_all/weather_id/day_of_year

    # Prepare X for ML: delet cols +  right order of cols
    X = pd.DataFrame()
    X = dSet.drop(["date", "dt"], axis=1)

    # right order model: temp/pressure/humidity/wind_speed/wind_deg/clouds_all/weather_id/clear_sky/day_of_year
    Z = X.iloc[:, [1, 2, 3, 4, 5, 6, 7, 0, 8]]

    power = mlp.predict(Z)
    P = pd.DataFrame(power, columns=["P_predicted"], dtype=np.int16)
    P_dSet = pd.concat([P, dSet], axis=1)

    # order: dt/clear_sky/P_predicted/temp/pressure/humidity/wind_speed/wind_deg/clouds_all/weather_id/day_of_year
    # and we drop comumn "date" by excluding '1'
    finalDataFrame = P_dSet.iloc[:, [3, 2, 0, 4, 5, 6, 7, 8, 9, 10, 11]]

    # Test: finalDataFrame = pd.DataFrame([[1, 2], [3, 4]])

    # Finetuning model
    # power before sunrise and after sunset to zero - model sometomes show small values
    finalDataFrame["P_predicted"] = finalDataFrame.apply(
        eliminate_power_outside_sunrise_sunset, axis=1
    )

    logging.info(f"ML succeeded returned:{finalDataFrame.info()}")
    return finalDataFrame

