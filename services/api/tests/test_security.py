import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends

from app.config import get_settings
from app.models import User
from app.security import (
    ALGORITHM,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)


def test_password_hash_is_argon2id_and_verifies():
    h = hash_password("correct-horse-9")
    assert h.startswith("$argon2id$")
    assert verify_password("correct-horse-9", h)
    assert not verify_password("wrong", h)
    assert not verify_password("x", "not-a-hash")


def test_token_claims():
    uid = uuid.uuid4()
    token, expires_in = create_access_token(uid)
    claims = jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
    assert claims["sub"] == str(uid)
    assert claims["exp"] - claims["iat"] == expires_in == 3600


def _whoami(app):
    @app.get("/_whoami")
    def whoami(user: User = Depends(get_current_user)):
        return {"email": user.email}


def test_dependency_accepts_valid_token(app, client, make_user):
    _whoami(app)
    _, headers = make_user("a@example.com")
    assert client.get("/_whoami", headers=headers).json() == {"email": "a@example.com"}


def test_dependency_rejects_missing_bad_expired_and_unknown_user(app, client):
    _whoami(app)
    secret = get_settings().jwt_secret
    now = datetime.now(UTC)
    expired = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
        },
        secret,
        algorithm=ALGORITHM,
    )
    wrong_key = jwt.encode(
        {"sub": str(uuid.uuid4()), "iat": now, "exp": now + timedelta(hours=1)},
        "x" * 40,
        algorithm=ALGORITHM,
    )
    unknown_user, _ = create_access_token(uuid.uuid4())
    for headers in (
        {},
        {"Authorization": "Bearer garbage"},
        {"Authorization": f"Bearer {expired}"},
        {"Authorization": f"Bearer {wrong_key}"},
        {"Authorization": f"Bearer {unknown_user}"},
    ):
        r = client.get("/_whoami", headers=headers)
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "unauthorized"
        assert r.headers["www-authenticate"] == "Bearer"
