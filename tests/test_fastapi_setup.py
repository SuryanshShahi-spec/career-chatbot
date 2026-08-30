from fastapi.testclient import TestClient

from Agent.app import fastapi_app


client = TestClient(fastapi_app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
