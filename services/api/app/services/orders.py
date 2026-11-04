"""Order persistence. Every query filters by owner_id: other users' rows don't exist here."""

import uuid
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, defer

from app.errors import ApiError
from app.models import Document, Order
from app.schemas import OrderCreate, OrderUpdate
from app.validation import FIELDS, Issue, validate_order
from app.validation.status import derive_status


def order_not_found() -> ApiError:
    return ApiError(404, "order_not_found", "Order not found.")


def _revalidate(order: Order, kept_extraction_issues: list[dict[str, Any]]) -> None:
    values = {f: getattr(order, f) for f in FIELDS}
    issues = validate_order(values)
    order.issues = [*(i.to_json() for i in issues), *kept_extraction_issues]
    kept = [Issue(**i) for i in kept_extraction_issues]
    order.status = derive_status(values, [*issues, *kept])


def list_orders(
    db: Session, owner_id: uuid.UUID, status: str | None, limit: int, offset: int
) -> tuple[list[Order], int]:
    where = [Order.owner_id == owner_id]
    if status:
        where.append(Order.status == status)
    total = db.scalar(select(func.count()).select_from(Order).where(*where)) or 0
    rows = db.scalars(
        select(Order)
        .where(*where)
        .options(defer(Order.extraction))
        .order_by(Order.created_at.desc(), Order.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return list(rows), total


def get_order(db: Session, owner_id: uuid.UUID, order_id: uuid.UUID, lock: bool = False) -> Order:
    stmt = select(Order).where(Order.id == order_id, Order.owner_id == owner_id)
    if lock:
        stmt = stmt.with_for_update(of=Order)
    order = db.scalar(stmt)
    if order is None:
        raise order_not_found()
    return order


def create_order(db: Session, owner_id: uuid.UUID, data: OrderCreate) -> Order:
    order = Order(owner_id=owner_id, **data.model_dump())
    _revalidate(order, [])
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def update_order(db: Session, owner_id: uuid.UUID, order_id: uuid.UUID, data: OrderUpdate) -> Order:
    order = get_order(db, owner_id, order_id, lock=True)
    edited = data.model_fields_set
    for field in edited:
        setattr(order, field, getattr(data, field))
    # Extraction-time issues stay until the user edits that field.
    kept = [i for i in order.issues if i["source"] == "extraction" and i["field"] not in edited]
    _revalidate(order, kept)
    db.commit()
    db.refresh(order)
    return order


def delete_order(db: Session, owner_id: uuid.UUID, order_id: uuid.UUID) -> None:
    order = get_order(db, owner_id, order_id, lock=True)
    if order.document_id is not None:
        # The FK cascades document -> order, so both go in this one transaction.
        db.execute(
            delete(Document).where(Document.id == order.document_id, Document.owner_id == owner_id)
        )
    else:
        db.execute(delete(Order).where(Order.id == order.id, Order.owner_id == owner_id))
    db.commit()
