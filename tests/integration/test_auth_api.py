from fastapi.testclient import TestClient

from src.main import app


def test_register_login_and_reject_bad_password():
    with TestClient(app) as client:
        register_resp = client.post(
            "/auth/register",
            json={
                "first_name": "Ada",
                "last_name": "Lovelace",
                "email": "ada.test@example.com",
                "password": "supersecret1",
            },
        )
        assert register_resp.status_code == 201

        duplicate_resp = client.post(
            "/auth/register",
            json={
                "first_name": "Ada",
                "last_name": "L",
                "email": "ada.test@example.com",
                "password": "supersecret1",
            },
        )
        assert duplicate_resp.status_code == 400

        login_resp = client.post(
            "/auth/login", json={"email": "ada.test@example.com", "password": "supersecret1"}
        )
        assert login_resp.status_code == 200
        assert "access_token" in login_resp.json()

        bad_login_resp = client.post(
            "/auth/login", json={"email": "ada.test@example.com", "password": "wrong"}
        )
        assert bad_login_resp.status_code == 401


def test_protected_endpoint_requires_auth():
    with TestClient(app) as client:
        resp = client.post(
            "/calls/outbound",
            json={
                "phone_number": "2015550123",
                "agent_name": "Sara",
                "greeting_message": "hi",
                "role_of_bot": "sales",
                "company_name": "Acme",
            },
        )
        assert resp.status_code == 401
