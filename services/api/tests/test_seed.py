import logging

from sqlalchemy import func, select

from app.config import get_settings
from app.models import User
from app.seed import main, parse, seed

SPEC = "rev1@genhealth.ai:first-secret-1,Rev2@genhealth.ai:second-secret-2"


def login(client, email, password):
    return client.post("/auth/login", data={"username": email, "password": password})


def test_seed_creates_both_users_who_can_log_in(client, db):
    """AC-M2.5"""
    r = seed(SPEC, db)
    assert (r.created, r.existing, r.skipped) == (2, 0, 0)
    assert login(client, "rev1@genhealth.ai", "first-secret-1").status_code == 200
    assert login(client, "rev2@genhealth.ai", "second-secret-2").status_code == 200


def test_rerun_changes_nothing_even_with_new_password(db):
    seed(SPEC, db)
    before = {u.email: u.password_hash for u in db.scalars(select(User))}
    r = seed("rev1@genhealth.ai:a-different-pw-9," + SPEC.split(",")[1], db)
    assert (r.created, r.existing) == (0, 2)
    after = {u.email: u.password_hash for u in db.scalars(select(User))}
    assert before == after
    assert db.scalar(select(func.count()).select_from(User)) == 2


def test_main_logs_counts_and_no_passwords(monkeypatch, caplog, capsys, client):
    monkeypatch.setenv("SEED_USERS", SPEC + ",broken-entry-with-secret-pw")
    get_settings.cache_clear()
    try:
        with caplog.at_level(logging.DEBUG):
            assert main() == 0
            assert main() == 0
    finally:
        get_settings.cache_clear()
    out = caplog.text + capsys.readouterr().out + capsys.readouterr().err
    assert "created=2 existing=0 skipped=1" in out
    assert "created=0 existing=2 skipped=1" in out
    for secret in ("first-secret-1", "second-secret-2", "broken-entry-with-secret-pw", "argon2"):
        assert secret not in out


def test_parse_rules():
    pairs, skipped = parse("a@b.co:pass:with:colons1, ,bad,x@y.co:short,@nope:12345678")
    assert pairs == [("a@b.co", "pass:with:colons1")]
    assert skipped == 3


def test_empty_spec_is_noop(monkeypatch, caplog):
    monkeypatch.setenv("SEED_USERS", "")
    get_settings.cache_clear()
    try:
        with caplog.at_level(logging.INFO):
            assert main() == 0
    finally:
        get_settings.cache_clear()
