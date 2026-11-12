"""Modelo relacional (SQLite): catálogo CPC, versiones del dataset y conjunto de oro.

Ver docs/modelo-datos.md para el diagrama ER y la fuente de cada regla.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

GOLD_STATUSES = ("pending", "confirmed", "corrected", "discarded")


class Base(DeclarativeBase):
    pass


class CpcCode(Base):
    __tablename__ = "cpc_code"
    __table_args__ = (
        CheckConstraint("length(code9) = 9", name="ck_cpc_code_len9"),
        CheckConstraint("code9 NOT GLOB '*[^0-9]*'", name="ck_cpc_code_digits"),
        CheckConstraint("substr(code9, 1, 5) = code5", name="ck_cpc_code_parent"),
        CheckConstraint("n_items >= 0", name="ck_cpc_code_items"),
    )

    code9: Mapped[str] = mapped_column(String(9), primary_key=True)
    code5: Mapped[str] = mapped_column(String(5), index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    n_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_year: Mapped[int] = mapped_column(Integer, nullable=False)
    last_year: Mapped[int] = mapped_column(Integer, nullable=False)


class DatasetVersion(Base):
    __tablename__ = "dataset_version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    config_hash: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    train_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    val_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    test_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    license: Mapped[str] = mapped_column(String(40), nullable=False)

    gold_items: Mapped[list[GoldItem]] = relationship(back_populates="dataset_version")


class GoldItem(Base):
    __tablename__ = "gold_item"
    __table_args__ = (
        UniqueConstraint("dataset_version_id", "desc_norm", name="uq_gold_version_desc"),
        CheckConstraint(f"status IN {GOLD_STATUSES!r}", name="ck_gold_status"),
        CheckConstraint(
            "(status IN ('pending', 'discarded')) OR (gold_code9 IS NOT NULL AND length(gold_code9) = 9)",
            name="ck_gold_code_when_reviewed",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_version_id: Mapped[int] = mapped_column(
        ForeignKey("dataset_version.id"), nullable=False
    )
    desc_norm: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    original_code9: Mapped[str] = mapped_column(String(9), nullable=False)
    gold_code9: Mapped[str | None] = mapped_column(String(9), nullable=True)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="pending")
    stratum: Mapped[str] = mapped_column(String(40), nullable=False)
    reviewer: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(String(500), nullable=False, default="")

    dataset_version: Mapped[DatasetVersion] = relationship(back_populates="gold_items")
