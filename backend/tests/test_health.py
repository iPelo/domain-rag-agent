from app.main import app
from fastapi.testclient import TestClient


# Smallest end-to-end test: spin up the app in-process with
# TestClient and hit /health. TestClient sends real requests
# through FastAPI without a running server — fast and offline.
def test_health_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["domain"] == "GermanLawRAG"
