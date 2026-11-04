import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Order, User
from app.schemas import OrderCreate, OrderList, OrderOut, OrderUpdate
from app.security import get_current_user
from app.services import orders as svc

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=OrderList)
def list_orders(
    status: Literal["needs_review", "ready"] | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    items, total = svc.list_orders(db, user.id, status, limit, offset)
    return {"items": items, "total": total}


@router.post("", status_code=201, response_model=OrderOut)
def create_order(
    body: OrderCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Order:
    return svc.create_order(db, user.id, body)


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Order:
    return svc.get_order(db, user.id, order_id)


@router.patch("/{order_id}", response_model=OrderOut)
def update_order(
    order_id: uuid.UUID,
    body: OrderUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Order:
    return svc.update_order(db, user.id, order_id, body)


@router.delete("/{order_id}", status_code=204)
def delete_order(
    order_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    svc.delete_order(db, user.id, order_id)
    return Response(status_code=204)
