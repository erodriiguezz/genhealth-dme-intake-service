import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.errors import ApiError
from app.models import User

ALGORITHM = "HS256"
_hasher = PasswordHasher()  # argon2id with argon2-cffi defaults
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

# Verified against when the email is unknown, so login timing doesn't reveal which emails exist.
DUMMY_HASH = _hasher.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: uuid.UUID) -> tuple[str, int]:
    s = get_settings()
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=s.jwt_ttl_min)
    token = jwt.encode(
        {"sub": str(user_id), "iat": now, "exp": exp}, s.jwt_secret, algorithm=ALGORITHM
    )
    return token, s.jwt_ttl_min * 60


def unauthorized() -> ApiError:
    return ApiError(
        401,
        "unauthorized",
        "Not authenticated.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    if not token:
        raise unauthorized()
    try:
        claims = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "exp", "iat"]},
        )
        user_id = uuid.UUID(claims["sub"])
    except (jwt.PyJWTError, ValueError):
        raise unauthorized() from None
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized()
    return user
