
from fastapi.testclient import TestClient

from src.api import app

client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["model_loaded"] is True


def test_prediction():
    payload = {
        "hour": 19,
        "weekday": 5,
        "promotion": 1,
        "weather": "rain",
        "zone": "central"
    }

    response = client.post("/predict", json=payload)

    assert response.status_code == 200

    result = response.json()

    assert "predicted_orders" in result
    assert result["predicted_orders"] >= 0
    assert result["unit"] == "orders"


def test_invalid_hour():
    payload = {
        "hour": 25,
        "weekday": 5,
        "promotion": 1,
        "weather": "rain",
        "zone": "central"
    }

    response = client.post("/predict", json=payload)

    assert response.status_code == 422
