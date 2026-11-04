import logging
import uuid
from datetime import date
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, undefer

from app.db import get_db
from app.errors import ApiError
from app.extraction import ExtractionError, ExtractionNotConfigured, FieldResult, get_extractor
from app.extraction.grounding import apply_grounding, normalize_npi, parse_dob
from app.models import Document, Order, User
from app.schemas import OrderOut
from app.security import get_current_user
from app.services import documents
from app.services.orders import order_not_found
from app.validation import FIELDS, Issue, validate_order
from app.validation.status import derive_status

log = logging.getLogger(__name__)
router = APIRouter(prefix="/orders", tags=["orders"])

RATE_LIMIT_MESSAGE = "Extraction limit reached (20 per hour). Try again later."


def _rate_limit(request: Request, user: User = Depends(get_current_user)) -> User:
    retry_after = request.app.state.extract_limiter.check(str(user.id))
    if retry_after is not None:
        raise ApiError(
            429, "rate_limited", RATE_LIMIT_MESSAGE, headers={"Retry-After": str(retry_after)}
        )
    return user


def _extraction_json(result: Any, grounded: dict[str, bool]) -> dict[str, Any]:
    return {
        "provider": result.provider,
        "model": result.model,
        "prompt_version": result.prompt_version,
        "latency_ms": result.latency_ms,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "fields": {
            name: {
                "raw": (f := result.fields.get(name) or FieldResult()).value,
                "evidence": f.evidence,
                "page": f.page,
                "grounded": grounded[name],
            }
            for name in FIELDS
        },
        "provider_candidates": [c.model_dump() for c in result.provider_candidates],
        "notes": result.notes,
    }


@router.post("/extract", status_code=201, response_model=OrderOut)
def extract_order(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(_rate_limit),
    db: Session = Depends(get_db),
) -> Order:
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > documents.MAX_BYTES + 1024 * 1024:
        raise ApiError(413, "file_too_large", "The PDF is larger than 20 MB.")
    upload = documents.load_upload(file.file, file.filename)

    try:
        result = get_extractor().extract(upload.content, upload.filename)
    except ExtractionNotConfigured:
        log.warning("extraction not configured")
        raise ApiError(
            503, "extraction_not_configured", "Extraction is not configured on this server."
        ) from None
    except ExtractionError:
        log.warning("extraction failed")
        raise ApiError(
            502, "extraction_failed", "Extraction failed or timed out. Please try again."
        ) from None

    fields, extraction_issues = apply_grounding(result)
    grounded = {n: f.value is not None for n, f in fields.items()}
    for name in FIELDS:
        fields.setdefault(name, FieldResult())
        grounded.setdefault(name, False)

    dob_raw = fields["patient_dob"].value
    dob: date | None = parse_dob(dob_raw)
    if dob_raw and dob is None:
        extraction_issues.append(
            Issue(
                "patient_dob",
                "dob.unparseable",
                "error",
                "The date of birth could not be read as a date. Enter it manually.",
                "extraction",
            ).to_json()
        )

    values: dict[str, Any] = {
        "patient_first_name": fields["patient_first_name"].value,
        "patient_last_name": fields["patient_last_name"].value,
        "patient_dob": dob,
        "provider_name": fields["provider_name"].value,
        "provider_npi": normalize_npi(fields["provider_npi"].value),
    }
    validation = validate_order(values)
    seen = {(i.field, i.code) for i in validation}
    extra = [i for i in extraction_issues if (i["field"], i["code"]) not in seen]
    issues = [*(i.to_json() for i in validation), *extra]
    status = derive_status(values, [*validation, *(Issue(**i) for i in extra)])

    doc_id, order_id = uuid.uuid4(), uuid.uuid4()
    document = Document(
        id=doc_id,
        owner_id=user.id,
        filename=upload.filename,
        sha256=upload.sha256,
        size_bytes=upload.size_bytes,
        page_count=upload.page_count,
        content=upload.content,
    )
    order = Order(
        id=order_id,
        owner_id=user.id,
        document_id=doc_id,
        status=status,
        issues=issues,
        extraction=_extraction_json(result, grounded),
        **values,
    )
    db.add(document)
    db.flush()
    db.add(order)
    db.commit()
    db.refresh(order)
    log.info("extracted order=%s status=%s latency_ms=%s", order.id, status, result.latency_ms)
    return order


def _content_disposition(filename: str) -> str:
    if filename.isascii():
        return f'inline; filename="{filename}"'
    fallback = filename.encode("ascii", "replace").decode().replace("?", "_")
    return f"inline; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename)}"


@router.get("/{order_id}/document")
def get_document(
    order_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    doc = db.scalar(
        select(Document)
        .join(Order, (Order.document_id == Document.id) & (Order.owner_id == Document.owner_id))
        .where(Order.id == order_id, Order.owner_id == user.id)
        .options(undefer(Document.content))
    )
    if doc is None:
        raise order_not_found()
    return Response(
        content=doc.content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": _content_disposition(doc.filename),
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
