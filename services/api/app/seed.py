"""Create reviewer accounts from SEED_USERS="email:pw,email:pw". Idempotent.

Existing users are never updated (so a changed env password doesn't silently rewrite a hash).
Passwords are never logged or printed, and neither are rejected entries (they contain one).
"""

import logging
import sys
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db import get_engine
from app.models import User
from app.schemas import EMAIL_SHAPE
from app.security import hash_password

log = logging.getLogger("app.seed")
MIN_PASSWORD = 8


@dataclass
class SeedResult:
    created: int = 0
    existing: int = 0
    skipped: int = 0


def parse(spec: str) -> tuple[list[tuple[str, str]], int]:
    pairs: list[tuple[str, str]] = []
    skipped = 0
    for entry in spec.split(","):
        if not entry.strip():
            continue
        email, sep, password = entry.partition(":")  # first colon: passwords may contain ':'
        email = email.strip()
        if not sep or not EMAIL_SHAPE.match(email) or len(password) < MIN_PASSWORD:
            skipped += 1
            continue
        pairs.append((email, password))
    return pairs, skipped


def seed(spec: str, session: Session) -> SeedResult:
    pairs, skipped = parse(spec)
    result = SeedResult(skipped=skipped)
    for email, password in pairs:
        if session.scalar(select(User.id).where(User.email == email)) is not None:
            result.existing += 1
            continue
        session.add(User(email=email, password_hash=hash_password(password)))
        result.created += 1
    session.commit()
    return result


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    spec = get_settings().seed_users
    if not spec.strip():
        log.info("seed: SEED_USERS is empty, nothing to do")
        return 0
    with sessionmaker(get_engine(), expire_on_commit=False)() as session:
        r = seed(spec, session)
    log.info("seed: created=%d existing=%d skipped=%d", r.created, r.existing, r.skipped)
    return 0


if __name__ == "__main__":
    sys.exit(main())
