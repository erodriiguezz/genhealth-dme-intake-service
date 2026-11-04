CREDS = {"email": "Mike@GenHealth.ai", "password": "correct-horse-9"}


def register(client, **over):
    return client.post("/auth/register", json={**CREDS, **over})


def login(client, username=CREDS["email"], password=CREDS["password"]):
    return client.post("/auth/login", data={"username": username, "password": password})


def test_register_returns_201_without_hash(client):
    r = register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "Mike@GenHealth.ai"
    assert set(body) == {"id", "email", "created_at"}


def test_register_duplicate_email_is_409_case_insensitive(client):
    assert register(client).status_code == 201
    r = register(client, email="mike@genhealth.ai")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "email_taken"


def test_register_short_password_is_422(client):
    r = register(client, password="Sh0rt!")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"
    assert "Sh0rt!" not in r.text  # input is never echoed back


def test_register_bad_email_and_long_password_are_422(client):
    assert register(client, email="nope").status_code == 422
    assert register(client, password="x" * 129).status_code == 422


def test_login_returns_bearer_token(client):
    register(client)
    r = login(client)
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "Mike@GenHealth.ai"


def test_login_is_case_insensitive_on_email(client):
    register(client)
    assert login(client, username="MIKE@genhealth.ai").status_code == 200


def test_login_bad_password_and_unknown_email_are_identical_401(client):
    register(client)
    bad = login(client, password="wrong-password")
    unknown = login(client, username="nobody@example.com")
    assert bad.status_code == unknown.status_code == 401
    assert bad.json() == unknown.json()
    assert bad.json()["error"]["code"] == "invalid_credentials"


def test_me_requires_token(client):
    r = client.get("/auth/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"
