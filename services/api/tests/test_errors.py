import logging

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db

PHI = "Marie-Curie-PHI-MARKER"


def test_integrity_error_logs_constraint_name_only(app, client, caplog, db):
    """AC-M2.6: an IntegrityError never logs row values."""
    db.execute(text("INSERT INTO users (email, password_hash) VALUES ('a@b.co', '$argon2id$x')"))
    db.commit()

    @app.post("/_boom")
    def boom(s: Session = Depends(get_db)):
        s.execute(
            text(
                "INSERT INTO orders (owner_id, status, patient_first_name) "
                "SELECT id, 'ready', :n FROM users"
            ),
            {"n": PHI},
        )

    with caplog.at_level(logging.DEBUG):
        r = client.post("/_boom")

    assert r.status_code == 422
    assert r.json()["error"]["code"] == "constraint_violation"
    assert PHI not in r.text
    assert PHI not in caplog.text
    assert "orders_ready_complete_chk" in caplog.text
