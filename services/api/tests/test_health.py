import pytest
from sqlalchemy.exc import OperationalError

from app import config
from app.db import get_db
from app.routers import health


def test_health_ok_with_db_up(client):  # AC-M1.1
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "db": "ok"}


def test_health_503_when_db_dependency_raises(app, client):  # AC-M1.5
    class Broken:
        def execute(self, *a, **k):
            raise OperationalError("SELECT 1", {}, Exception("secret host detail"))

    app.dependency_overrides[get_db] = lambda: Broken()
    r = client.get("/health")
    assert r.status_code == 503
    assert r.json() == {"status": "degraded", "db": "down"}


def test_health_503_on_statement_timeout(client, monkeypatch):  # AC-M1.5
    monkeypatch.setenv("HEALTH_TIMEOUT_MS", "100")
    config.get_settings.cache_clear()
    monkeypatch.setattr(health, "CHECK_SQL", "SELECT pg_sleep(2)")
    try:
        r = client.get("/health")
    finally:
        config.get_settings.cache_clear()
    assert r.status_code == 503
    assert r.json() == {"status": "degraded", "db": "down"}


@pytest.mark.parametrize("url", ["postgres://u:p@h/db", "postgresql://u:p@h/db"])
def test_database_url_normalized(url):
    assert config.Settings(database_url=url).database_url == "postgresql+psycopg://u:p@h/db"


def test_cors_origins_comma_list():
    s = config.Settings(cors_origins="https://a.app, http://localhost:3000")
    assert s.cors_origins == ["https://a.app", "http://localhost:3000"]


def test_cors_origins_trailing_slash_stripped():  # AC-M1.4
    s = config.Settings(cors_origins="https://a.app/, http://localhost:3000/")
    assert s.cors_origins == ["https://a.app", "http://localhost:3000"]


def test_cors_middleware_allows_only_listed_origins(monkeypatch):  # AC-M1.4
    from fastapi.testclient import TestClient

    from app.main import create_app

    monkeypatch.setenv("CORS_ORIGINS", "https://ok.app,https://slash.app/")
    config.get_settings.cache_clear()
    try:
        c = TestClient(create_app())
        ok = c.get("/health", headers={"Origin": "https://ok.app"})
        slash = c.get("/health", headers={"Origin": "https://slash.app"})
        bad = c.get("/health", headers={"Origin": "https://evil.app"})
    finally:
        config.get_settings.cache_clear()
    assert ok.headers["access-control-allow-origin"] == "https://ok.app"
    assert slash.headers["access-control-allow-origin"] == "https://slash.app"
    assert "access-control-allow-origin" not in bad.headers
