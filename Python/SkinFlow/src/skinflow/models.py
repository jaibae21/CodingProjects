"""Persistence models. Services own validation and transactions."""

from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand: Mapped[str] = mapped_column(String(200))
    name: Mapped[str] = mapped_column(String(250))
    category: Mapped[str] = mapped_column(String(80))
    ingredients: Mapped[str] = mapped_column(Text, default="")
    ingredients_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    actives: Mapped[str] = mapped_column(Text, default="")
    purpose: Mapped[str] = mapped_column(Text, default="")
    instructions: Mapped[str] = mapped_column(Text, default="")
    frequency: Mapped[str] = mapped_column(String(250), default="")
    suitability: Mapped[str] = mapped_column(String(10), default="AM/PM")
    date_added: Mapped[date] = mapped_column(Date, default=date.today)
    opened_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    expires_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiration_notes: Mapped[str] = mapped_column(Text, default="")
    image_path: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="Active")
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    @property
    def label(self) -> str:
        return f"{self.brand} {self.name}".strip()


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)


class PlanRevision(Base):
    __tablename__ = "plan_revisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    description: Mapped[str] = mapped_column(String(250))
    payload: Mapped[dict] = mapped_column(JSON)


class Completion(Base):
    __tablename__ = "completions"
    __table_args__ = (UniqueConstraint("day", "period", "step_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date)
    period: Mapped[str] = mapped_column(String(2))
    step_id: Mapped[str] = mapped_column(String(100))
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    label: Mapped[str] = mapped_column(Text)
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
