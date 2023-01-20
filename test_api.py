from fastapi.testclient import TestClient

from app import app

test_site = {
    "date": "20-01-2023",
    "location": {"lat": 51.0, "lng": 3.11},
    "altitude": 70,
    "tilt": 35,
    "azimuth": 170,
    "totalWattPeak": 7400,
    "wattInvertor": 5040,
    "timezone": "Europe/Brussels",
}

client = TestClient(app)


def test_api_get():
    response = client.get("/")
    assert response.status_code == 200


def test_api_post_forecast():
    response = client.post("/forecast", json=test_site)
    assert response.status_code == 200


def test_api_post_forecast_with_query_params():
    response = client.post("/forecast?provider=openmeteo", json=test_site)
    assert response.status_code == 200


def test_api_post_clearsky():
    response = client.post("/clearsky", json=test_site)
    assert response.status_code == 200
