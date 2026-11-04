import uuid

import pytest

VALID = {
    "patient_first_name": "Jane",
    "patient_last_name": "Doe",
    "patient_dob": "1961-03-14",
    "provider_name": "Ann Lee MD",
    "provider_npi": "1234567893",
}


@pytest.fixture
def auth(make_user):
    return make_user("owner@example.com")[1]


def codes(order):
    return sorted(i["code"] for i in order["issues"])


def test_crud_round_trip(client, auth):
    """AC-M2.2"""
    r = client.post("/orders", json=VALID, headers=auth)
    assert r.status_code == 201
    created = r.json()
    assert created["status"] == "ready"
    assert created["issues"] == []
    assert created["extraction"] is None and created["document"] is None
    oid = created["id"]

    got = client.get(f"/orders/{oid}", headers=auth)
    assert got.status_code == 200 and got.json() == created

    p = client.patch(f"/orders/{oid}", json={"provider_name": "Ann Lee, MD"}, headers=auth)
    assert p.status_code == 200
    assert p.json()["provider_name"] == "Ann Lee, MD"
    assert client.get(f"/orders/{oid}", headers=auth).json()["provider_name"] == "Ann Lee, MD"

    listing = client.get("/orders", headers=auth).json()
    assert listing["total"] == 1
    assert listing["items"][0]["id"] == oid
    assert "extraction" not in listing["items"][0]

    assert client.delete(f"/orders/{oid}", headers=auth).status_code == 204
    assert client.get(f"/orders/{oid}", headers=auth).status_code == 404
    assert client.patch(f"/orders/{oid}", json={}, headers=auth).status_code == 404
    assert client.delete(f"/orders/{oid}", headers=auth).status_code == 404
    assert client.get("/orders", headers=auth).json() == {"items": [], "total": 0}


def test_list_filter_and_pagination(client, auth):
    for i in range(3):
        client.post("/orders", json={**VALID, "patient_first_name": f"Jane{'x' * i}"}, headers=auth)
    client.post("/orders", json={}, headers=auth)
    assert client.get("/orders", headers=auth).json()["total"] == 4
    ready = client.get("/orders?status=ready", headers=auth).json()
    assert ready["total"] == 3
    page = client.get("/orders?limit=2&offset=3", headers=auth).json()
    assert page["total"] == 4 and len(page["items"]) == 1
    # newest first
    newest = client.get("/orders?limit=1", headers=auth).json()["items"][0]
    assert newest["status"] == "needs_review"
    assert client.get("/orders?status=bogus", headers=auth).status_code == 422
    assert client.get("/orders?limit=101", headers=auth).status_code == 422


def test_invalid_npi_saved_as_given_then_fixed(client, auth):
    """AC-M2.4"""
    r = client.post("/orders", json={**VALID, "provider_npi": "9182734556"}, headers=auth)
    o = r.json()
    assert o["provider_npi"] == "9182734556"
    assert o["status"] == "needs_review"
    assert "npi.checksum_failed" in codes(o)

    fixed = client.patch(f"/orders/{o['id']}", json={"provider_npi": "1234567893"}, headers=auth)
    assert fixed.json()["status"] == "ready"
    assert fixed.json()["issues"] == []


def test_missing_fields_become_not_found_issues(client, auth):
    o = client.post("/orders", json={}, headers=auth).json()
    assert o["status"] == "needs_review"
    assert codes(o) == [
        "patient_dob.not_found",
        "patient_first_name.not_found",
        "patient_last_name.not_found",
        "provider_name.not_found",
        "provider_npi.not_found",
    ]
    # null clears a field, which then reports not_found again
    ok = client.post("/orders", json=VALID, headers=auth).json()
    cleared = client.patch(f"/orders/{ok['id']}", json={"provider_npi": None}, headers=auth).json()
    assert codes(cleared) == ["provider_npi.not_found"]
    assert cleared["status"] == "needs_review"


def test_future_dob_is_error_and_1900_is_warning(client, auth):
    future = client.post("/orders", json={**VALID, "patient_dob": "2999-01-01"}, headers=auth)
    assert future.json()["status"] == "needs_review"
    assert codes(future.json()) == ["dob.in_future"]

    old = client.post("/orders", json={**VALID, "patient_dob": "1900-12-05"}, headers=auth).json()
    assert old["status"] == "ready"
    assert [(i["code"], i["severity"]) for i in old["issues"]] == [("dob.age_over_120", "warning")]


def test_invalid_names_stored_as_given(client, auth):
    o = client.post("/orders", json={**VALID, "patient_first_name": " Mar1e   Anne "}, headers=auth)
    assert o.json()["patient_first_name"] == "Mar1e Anne"  # trimmed and collapsed only
    assert codes(o.json()) == ["name.invalid_chars"]


def test_npi_separators_stripped(client, auth):
    o = client.post("/orders", json={**VALID, "provider_npi": "1234-567 893"}, headers=auth).json()
    assert o["provider_npi"] == "1234567893" and o["status"] == "ready"


def test_non_iso_dob_is_422(client, auth):
    r = client.post("/orders", json={**VALID, "patient_dob": "12/05/1961"}, headers=auth)
    assert r.status_code == 422


@pytest.mark.parametrize("key", ["status", "owner_id", "issues", "extraction", "id", "document_id"])
def test_server_owned_keys_rejected(client, auth, key):
    value = "ready" if key == "status" else str(uuid.uuid4())
    assert client.post("/orders", json={key: value}, headers=auth).status_code == 422
    oid = client.post("/orders", json={}, headers=auth).json()["id"]
    assert client.patch(f"/orders/{oid}", json={key: value}, headers=auth).status_code == 422


def test_patch_drops_extraction_issues_only_for_edited_fields(client, auth, make_user, db):
    from sqlalchemy import update

    from app.models import Order

    oid = client.post("/orders", json=VALID, headers=auth).json()["id"]
    extraction_issues = [
        {
            "field": "provider_name",
            "code": "provider.multiple_candidates",
            "severity": "warning",
            "message": "m",
            "source": "extraction",
        },
        {
            "field": "patient_last_name",
            "code": "patient_last_name.ungrounded",
            "severity": "error",
            "message": "m",
            "source": "extraction",
        },
    ]
    db.execute(
        update(Order)
        .where(Order.id == uuid.UUID(oid))
        .values(issues=extraction_issues, status="needs_review")
    )
    db.commit()

    r = client.patch(f"/orders/{oid}", json={"provider_name": "Ann Lee MD"}, headers=auth).json()
    assert codes(r) == ["patient_last_name.ungrounded"]
    assert r["status"] == "needs_review"  # the unresolved extraction error still blocks ready

    r = client.patch(f"/orders/{oid}", json={"patient_last_name": "Doe"}, headers=auth).json()
    assert r["issues"] == [] and r["status"] == "ready"


def test_unknown_id_is_404_and_malformed_id_is_422(client, auth):
    assert client.get(f"/orders/{uuid.uuid4()}", headers=auth).status_code == 404
    assert client.get("/orders/not-a-uuid", headers=auth).status_code == 422
