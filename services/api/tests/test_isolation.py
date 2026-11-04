import uuid

from sqlalchemy import text

VALID = {
    "patient_first_name": "Jane",
    "patient_last_name": "Doe",
    "patient_dob": "1961-03-14",
    "provider_name": "Ann Lee MD",
    "provider_npi": "1234567893",
}


def test_isolation(client, make_user):
    """AC-M2.3"""
    _, a = make_user("a@example.com")
    _, b = make_user("b@example.com")
    oid = client.post("/orders", json=VALID, headers=a).json()["id"]

    for r in (
        client.get(f"/orders/{oid}", headers=b),
        client.patch(f"/orders/{oid}", json={"provider_name": "Hacked"}, headers=b),
        client.delete(f"/orders/{oid}", headers=b),
    ):
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "order_not_found"

    assert client.get("/orders", headers=b).json() == {"items": [], "total": 0}
    mine = client.get(f"/orders/{oid}", headers=a).json()
    assert mine["provider_name"] == "Ann Lee MD"  # untouched by B's attempts


def test_unauthenticated_is_401(client):
    oid = uuid.uuid4()
    for r in (
        client.get("/orders"),
        client.post("/orders", json={}),
        client.get(f"/orders/{oid}"),
        client.patch(f"/orders/{oid}", json={}),
        client.delete(f"/orders/{oid}"),
    ):
        assert r.status_code == 401


def test_each_user_lists_only_their_own(client, make_user):
    _, a = make_user("a@example.com")
    _, b = make_user("b@example.com")
    for _ in range(2):
        client.post("/orders", json=VALID, headers=a)
    client.post("/orders", json={}, headers=b)
    assert client.get("/orders", headers=a).json()["total"] == 2
    assert client.get("/orders", headers=b).json()["total"] == 1
    assert client.get("/orders?status=ready", headers=b).json()["total"] == 0


def test_database_rejects_order_pointing_at_another_users_document(make_user, db):
    """Composite FK (document_id, owner_id): the DB backs up the API's scoping."""
    import pytest
    from sqlalchemy.exc import IntegrityError

    a, _ = make_user("a@example.com")
    b, _ = make_user("b@example.com")
    doc_id = uuid.uuid4()
    db.execute(
        text(
            "INSERT INTO documents (id, owner_id, filename, sha256, size_bytes, page_count,"
            " content)"
            " VALUES (:id, :o, 'f.pdf', :h, 3, 1, '\\x010203')"
        ),
        {"id": doc_id, "o": a.id, "h": "0" * 64},
    )
    with pytest.raises(IntegrityError) as exc:
        db.execute(
            text("INSERT INTO orders (owner_id, document_id) VALUES (:o, :d)"),
            {"o": b.id, "d": doc_id},
        )
    assert exc.value.orig.diag.constraint_name == "orders_document_owner_fk"
    db.rollback()


def test_deleting_an_order_with_a_document_removes_both(client, make_user, db):
    user, auth = make_user("a@example.com")
    doc_id = uuid.uuid4()
    db.execute(
        text(
            "INSERT INTO documents (id, owner_id, filename, sha256, size_bytes, page_count,"
            " content)"
            " VALUES (:id, :o, 'f.pdf', :h, 3, 1, '\\x010203')"
        ),
        {"id": doc_id, "o": user.id, "h": "0" * 64},
    )
    oid = db.scalar(
        text("INSERT INTO orders (owner_id, document_id) VALUES (:o, :d) RETURNING id"),
        {"o": user.id, "d": doc_id},
    )
    db.commit()

    shown = client.get(f"/orders/{oid}", headers=auth).json()
    assert shown["document"]["filename"] == "f.pdf"
    assert "content" not in shown["document"]

    assert client.delete(f"/orders/{oid}", headers=auth).status_code == 204
    assert db.scalar(text("SELECT count(*) FROM documents")) == 0
