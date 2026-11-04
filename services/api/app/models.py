import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, ForeignKeyConstraint, String, Text, func, text
from sqlalchemy.dialects.postgresql import BYTEA, CITEXT, JSONB, UUID
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, deferred, mapped_column, relationship

ORDER_STATUS = PGEnum("needs_review", "ready", name="order_status", create_type=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(CITEXT, unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int]
    page_count: Mapped[int]
    content: Mapped[bytes] = deferred(mapped_column(BYTEA))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "owner_id"],
            ["documents.id", "documents.owner_id"],
            name="orders_document_owner_fk",
            ondelete="CASCADE",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), unique=True)
    status: Mapped[str] = mapped_column(ORDER_STATUS, server_default="needs_review")
    patient_first_name: Mapped[str | None] = mapped_column(Text)
    patient_last_name: Mapped[str | None] = mapped_column(Text)
    patient_dob: Mapped[date | None] = mapped_column(Date)
    provider_name: Mapped[str | None] = mapped_column(Text)
    provider_npi: Mapped[str | None] = mapped_column(String(20))
    issues: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    extraction: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped[Document | None] = relationship(
        primaryjoin="Order.document_id == Document.id",
        foreign_keys=[document_id],
        viewonly=True,
        lazy="joined",
    )
