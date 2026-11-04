import io
import logging
from pathlib import Path

import pypdf
import pytest
from sqlalchemy import text

from app.extraction import ExtractionError, ExtractionNotConfigured, ExtractionResult, FieldResult
from app.extraction.fake import FakeExtractor
from app.routers import extract as extract_router
from app.services import documents

CASES = Path(__file__).resolve().parents[3] / "evals" / "cases"
PDF = (CASES / "genhealth-cpap-fax.pdf").read_bytes()


def upload(client, headers, content=PDF, name="fax.pdf"):
    return client.post(
        "/orders/extract", headers=headers, files={"file": (name, content, "application/pdf")}
    )


def counts(db):
    db.rollback()
    return db.execute(
        text("SELECT (SELECT count(*) FROM orders), (SELECT count(*) FROM documents)")
    ).one()


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setattr(extract_router, "get_extractor", lambda: FakeExtractor())


def codes(body):
    return {i["code"] for i in body["issues"]}


def test_ac_m3_1_benchmark_shape(client, make_user, fake):
    _, h = make_user()
    r = upload(client, h)
    assert r.status_code == 201
    b = r.json()
    assert (b["patient_first_name"], b["patient_last_name"]) == ("Marie", "Curie")
    assert b["patient_dob"] == "1900-12-05"
    assert b["provider_name"] == "Arjun Raj D.P.M"
    assert b["provider_npi"] == "9182734556"
    assert b["status"] == "needs_review"
    assert {"npi.checksum_failed", "npi.prefix", "dob.age_over_120"} <= codes(b)
    multi = next(i for i in b["issues"] if i["code"] == "provider.multiple_candidates")
    assert multi["severity"] == "warning"
    ex = b["extraction"]
    assert ex["provider"] == "fake" and ex["prompt_version"] and "latency_ms" in ex
    assert len(ex["provider_candidates"]) == 2
    for f in ex["fields"].values():
        assert f["evidence"] and f["page"] == 1 and f["grounded"] is True
    assert b["document"]["page_count"] == 4
    assert b["document"]["filename"] == "fax.pdf"


class Stub:
    def __init__(self, **overrides):
        self.overrides = overrides

    def extract(self, pdf_bytes, filename):
        res = FakeExtractor().extract(pdf_bytes, filename)
        res.fields.update(self.overrides)
        return res


def use(monkeypatch, stub):
    monkeypatch.setattr(extract_router, "get_extractor", lambda: stub)


def test_ac_m3_2_ungrounded_value_is_dropped(client, make_user, monkeypatch):
    _, h = make_user()
    bad = FieldResult(value="Pierre", evidence="Marie Curie", page=1)
    use(monkeypatch, Stub(patient_first_name=bad))
    b = upload(client, h).json()
    assert b["patient_first_name"] is None
    assert "patient_first_name.ungrounded" in codes(b)
    assert "patient_first_name.not_found" not in codes(b)
    f = b["extraction"]["fields"]["patient_first_name"]
    assert f["raw"] == "Pierre" and f["grounded"] is False
    assert b["status"] == "needs_review"


def test_ac_m3_2_missing_dob_is_not_found(client, make_user, monkeypatch):
    _, h = make_user()
    use(monkeypatch, Stub(patient_dob=FieldResult()))
    b = upload(client, h).json()
    assert b["patient_dob"] is None
    assert "patient_dob.not_found" in codes(b)


def test_ac_m3_2_unparseable_dob_keeps_raw(client, make_user, monkeypatch):
    _, h = make_user()
    dob = FieldResult(value="13/45/1980", evidence="DOB 13/45/1980", page=1)
    use(monkeypatch, Stub(patient_dob=dob))
    b = upload(client, h).json()
    assert b["patient_dob"] is None
    assert "dob.unparseable" in codes(b)
    assert "patient_dob.not_found" not in codes(b)
    assert next(i for i in b["issues"] if i["code"] == "dob.unparseable")["source"] == "validation"
    assert b["extraction"]["fields"]["patient_dob"]["raw"] == "13/45/1980"


class _Single:
    """Wraps a stub and drops the second provider candidate."""

    def __init__(self, inner):
        self.inner = inner

    def extract(self, pdf_bytes, filename):
        res = self.inner.extract(pdf_bytes, filename)
        return ExtractionResult(**{**res.model_dump(), "provider_candidates": []})


def test_ac_m3_2_clean_extraction_is_ready(client, make_user, monkeypatch):
    _, h = make_user()
    stub = Stub(
        patient_dob=FieldResult(value="03/14/1962", evidence="DOB 03/14/1962", page=1),
        provider_npi=FieldResult(value="1245319599", evidence="NPI 1245319599", page=1),
    )
    use(monkeypatch, _Single(stub))
    b = upload(client, h).json()
    assert b["status"] == "ready", b["issues"]
    assert b["patient_dob"] == "1962-03-14"


def test_ac_m3_3_not_a_pdf_415(client, make_user, fake, db):
    _, h = make_user()
    r = upload(client, h, b"hello world", "x.pdf")
    assert r.status_code == 415
    assert r.json()["error"]["code"] == "unsupported_media_type"
    assert tuple(counts(db)) == (0, 0)


def test_ac_m3_3_too_large_413(client, make_user, fake, db, monkeypatch):
    _, h = make_user()
    monkeypatch.setattr(documents, "MAX_BYTES", 1000)
    r = upload(client, h, b"%PDF-" + b"0" * 2000)
    assert r.status_code == 413
    assert tuple(counts(db)) == (0, 0)


def test_ac_m3_3_corrupt_pdf_422(client, make_user, fake, db):
    _, h = make_user()
    r = upload(client, h, b"%PDF-1.4\nthis is not a real pdf")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_pdf"
    assert tuple(counts(db)) == (0, 0)


def test_ac_m3_3_encrypted_pdf_422(client, make_user, fake, db):
    _, h = make_user()
    w = pypdf.PdfWriter()
    w.add_blank_page(100, 100)
    w.encrypt("secret")
    buf = io.BytesIO()
    w.write(buf)
    r = upload(client, h, buf.getvalue())
    assert r.status_code == 422
    assert tuple(counts(db)) == (0, 0)


def test_ac_m3_3_too_many_pages_422(client, make_user, fake, db):
    _, h = make_user()
    w = pypdf.PdfWriter()
    for _ in range(101):
        w.add_blank_page(50, 50)
    buf = io.BytesIO()
    w.write(buf)
    r = upload(client, h, buf.getvalue())
    assert r.status_code == 422
    assert tuple(counts(db)) == (0, 0)


def test_ac_m3_3_unauthenticated_401(client, fake, db):
    r = client.post("/orders/extract", files={"file": ("a.pdf", PDF, "application/pdf")})
    assert r.status_code == 401
    assert tuple(counts(db)) == (0, 0)


def test_ac_m3_3_missing_file_422(client, make_user, fake):
    _, h = make_user()
    assert client.post("/orders/extract", headers=h).status_code == 422


def test_ac_m3_3_rate_limit_429(client, make_user, fake):
    _, h = make_user()
    client.app.state.extract_limiter.limit = 2
    assert upload(client, h).status_code == 201
    assert upload(client, h).status_code == 201
    r = upload(client, h)
    assert r.status_code == 429 and "retry-after" in r.headers


def test_ac_m3_3_filename_sanitized(client, make_user, fake):
    _, h = make_user()
    b = upload(client, h, name="../../etc/pass wd\\evil.pdf").json()
    assert b["document"]["filename"] == "evil.pdf"
    assert documents.sanitize_filename('a"b\x00c.pdf') == "abc.pdf"
    assert documents.sanitize_filename('a"b\x00c.pdf') == "abc.pdf"
    assert documents.sanitize_filename("a" * 400)[:3] == "aaa"
    assert len(documents.sanitize_filename("a" * 400)) == 255
    assert documents.sanitize_filename("") == "document.pdf"


def test_ac_m3_4_owner_downloads_pdf_other_gets_404(client, make_user, fake):
    _, a = make_user()
    _, other = make_user()
    oid = upload(client, a).json()["id"]
    r = client.get(f"/orders/{oid}/document", headers=a)
    assert r.status_code == 200
    assert r.content == PDF
    assert r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"] == 'inline; filename="fax.pdf"'
    assert r.headers["cache-control"] == "private, no-store"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert client.get(f"/orders/{oid}/document", headers=other).status_code == 404
    assert client.get(f"/orders/{oid}/document").status_code == 401


def test_ac_m3_4_manual_order_has_no_document(client, make_user):
    _, h = make_user()
    oid = client.post("/orders", json={}, headers=h).json()["id"]
    assert client.get(f"/orders/{oid}/document", headers=h).status_code == 404


class Boom:
    def __init__(self, exc):
        self.exc = exc

    def extract(self, pdf_bytes, filename):
        raise self.exc


@pytest.mark.parametrize(
    ("exc", "status", "code"),
    [
        (ExtractionError("PHI Marie Curie timeout"), 502, "extraction_failed"),
        (ExtractionNotConfigured("no key"), 503, "extraction_not_configured"),
    ],
)
def test_ac_m3_5_extractor_failures_save_nothing(
    client, make_user, monkeypatch, db, caplog, exc, status, code
):
    _, h = make_user()
    use(monkeypatch, Boom(exc))
    with caplog.at_level(logging.DEBUG):
        r = upload(client, h, name="Marie-Curie-secret.pdf")
    assert r.status_code == status
    assert r.json()["error"]["code"] == code
    assert tuple(counts(db)) == (0, 0)
    log_text = caplog.text
    for phi in ("Marie", "Curie", "secret", "9182734556"):
        assert phi not in log_text


def test_ac_m3_5_no_phi_in_logs_on_success(client, make_user, fake, caplog):
    _, h = make_user()
    with caplog.at_level(logging.DEBUG):
        assert upload(client, h, name="Marie-Curie.pdf").status_code == 201
    for phi in ("Marie", "Curie", "9182734556", "Arjun"):
        assert phi not in caplog.text


def test_ac_m3_3_oversized_content_length_rejected_before_parsing(client, make_user):
    _, h = make_user()
    r = client.post(
        "/orders/extract",
        headers={**h, "Content-Length": str(documents.MAX_BYTES + 2 * 1024 * 1024)},
        content=b"x",
    )
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "file_too_large"


def test_ac_m3_3_chunked_body_over_cap_rejected(client, make_user, monkeypatch):
    from app import upload_limit

    monkeypatch.setattr(upload_limit, "MAX_BYTES", 1000)
    monkeypatch.setattr(upload_limit, "SLACK", 100)
    _, h = make_user()

    def chunks():
        for _ in range(5):
            yield b"x" * 500

    r = client.post(
        "/orders/extract",
        headers={**h, "Content-Type": "multipart/form-data; boundary=b"},
        content=chunks(),
    )
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "file_too_large"
