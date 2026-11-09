def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["product"] == "VERITAS"
    assert "Truth" in data["tagline"]


def test_user_registration(client):
    payload = {
        "email": "new.scientist@veritas.org",
        "password": "SecurePassword987!",
        "full_name": "Dr. Alan Turing"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == payload["email"]
    assert data["user"]["full_name"] == payload["full_name"]


def test_user_duplicate_registration_fails(client, test_user):
    payload = {
        "email": test_user.email,
        "password": "AnyPassword123!",
        "full_name": "Duplicate User"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_user_login_success(client, test_user):
    payload = {
        "email": test_user.email,
        "password": "VeritasPassword123!"
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


def test_user_login_invalid_password(client, test_user):
    payload = {
        "email": test_user.email,
        "password": "WrongPassword!"
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401


def test_get_current_user_profile(client, auth_headers, test_user):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user.id
    assert data["email"] == test_user.email
