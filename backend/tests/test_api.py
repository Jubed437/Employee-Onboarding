from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_personas_are_public() -> None:
    response = client.get("/api/v1/auth/personas")

    assert response.status_code == 200
    assert response.json()[0]["role"] == "ADMIN"


def test_login_returns_jwt() -> None:
    response = client.post("/api/v1/auth/login", json={"user_id": "admin-1"})

    assert response.status_code == 200
    assert response.json()["user"]["id"] == "admin-1"
    assert response.json()["token"]


def test_protected_route_rejects_missing_token() -> None:
    response = client.get("/api/v1/hires")

    assert response.status_code == 401


def test_protected_route_rejects_wrong_role() -> None:
    token = client.post("/api/v1/auth/login", json={"user_id": "payroll-1"}).json()["token"]

    response = client.get("/api/v1/hires", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
