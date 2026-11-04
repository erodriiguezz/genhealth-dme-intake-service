CREDS = {"email": "Mike@GenHealth.ai", "password": "correct-horse-9"}


def register(client, **over):
    return client.post("/auth/register", json={**CREDS, **over})


def login(client, username=CREDS["email"], password=CREDS["password"]):
    return client.post("/auth/login", data={"username": username, "password": password})


def test_ac_m2_1_register_returns_201_without_hash(client):
    r = register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "Mike@GenHealth.ai"
    assert set(body) == {"id", "email", "created_at"}


def test_ac_m2_1_register_duplicate_email_is_409_case_insensitive(client):
    assert register(client).status_code == 201
    r = register(client, email="mike@genhealth.ai")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "email_taken"


def test_ac_m2_1_register_short_password_is_422(client):
    r = register(client, password="Sh0rt!")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"
    assert "Sh0rt!" not in r.text  # input is never echoed back


def test_ac_m2_1_register_bad_email_and_long_password_are_422(client):
    assert register(client, email="nope").status_code == 422
    assert register(client, password="x" * 129).status_code == 422


def test_ac_m2_1_login_returns_bearer_token(client):
    register(client)
    r = login(client)
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "Mike@GenHealth.ai"


def test_ac_m2_1_login_is_case_insensitive_on_email(client):
    register(client)
    assert login(client, username="MIKE@genhealth.ai").status_code == 200


def test_ac_m2_1_login_bad_password_and_unknown_email_are_identical_401(client):
    register(client)
    bad = login(client, password="wrong-password")
    unknown = login(client, username="nobody@example.com")
    assert bad.status_code == unknown.status_code == 401
    assert bad.json() == unknown.json()
    assert bad.json()["error"]["code"] == "invalid_credentials"


def test_ac_m2_1_me_requires_token(client):
    r = client.get("/auth/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_login_and_register_are_rate_limited_per_ip(client):
    for _ in range(10):
        assert login(client, password="wrong-password").status_code == 401
    r = login(client, password="wrong-password")
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "rate_limited"
    assert int(r.headers["retry-after"]) >= 1
    assert register(client).status_code == 429  # same IP, same budget


def test_rate_limit_is_keyed_by_ip(client):
    for _ in range(10):
        login(client, password="x")
    assert login(client).status_code == 429
    other = client.post(
        "/auth/login",
        data={"username": "a@b.co", "password": "x"},
        headers={"X-Forwarded-For": "203.0.113.9"},
    )
    assert other.status_code == 401


def test_rate_limiter_window_expires():
    from app.ratelimit import RateLimiter

    rl = RateLimiter(limit=2, window_s=0.05)
    assert rl.check("k") is None and rl.check("k") is None
    assert rl.check("k") is not None
    import time

    time.sleep(0.06)
    assert rl.check("k") is None
