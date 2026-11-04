import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://intake:intake@localhost:55433/intake_test"
)
os.environ["ENV"] = "test"
os.environ["SEED_USERS"] = ""

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from alembic import command  # noqa: E402
from app.db import get_engine  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import User  # noqa: E402
from app.security import create_access_token, hash_password  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    cfg = Config(os.path.join(ROOT, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(ROOT, "alembic"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    """Per-test isolation: the app commits on its own connections, so truncate afterwards."""
    yield
    with get_engine().begin() as conn:
        conn.execute(text("TRUNCATE users CASCADE"))


@pytest.fixture
def db():
    with Session(get_engine(), expire_on_commit=False) as session:
        yield session


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def make_user(db):
    """Insert a user directly (no rate-limited HTTP call). Returns (user, auth headers)."""
    counter = iter(range(10_000))

    def _make(email: str | None = None, password: str = "correct-horse-9"):
        user = User(
            email=email or f"user{next(counter)}@example.com",
            password_hash=hash_password(password),
        )
        db.add(user)
        db.commit()
        token, _ = create_access_token(user.id)
        return user, {"Authorization": f"Bearer {token}"}

    return _make
