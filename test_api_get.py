from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_api_get():
    response = client.get("/")
    assert response.status_code == 200
