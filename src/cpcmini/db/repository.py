"""Acceso a datos con consultas parametrizadas (SQLAlchemy; nunca SQL concatenado)."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from cpcmini.db.models import CpcCode, DatasetVersion, GoldItem


def make_engine(url: str) -> Engine:
    return create_engine(url, future=True, pool_pre_ping=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@dataclass(frozen=True)
class CatalogEntry:
    code9: str
    code5: str
    label: str
    n_items: int


class CatalogRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, code9: str) -> CatalogEntry | None:
        row = self.session.get(CpcCode, code9)
        return _entry(row) if row else None

    def get_many(self, codes: Iterable[str]) -> dict[str, CatalogEntry]:
        wanted = list(set(codes))
        if not wanted:
            return {}
        rows = self.session.scalars(select(CpcCode).where(CpcCode.code9.in_(wanted)))
        return {r.code9: _entry(r) for r in rows}

    def search(self, text: str, limit: int) -> list[CatalogEntry]:
        """Búsqueda por código o por palabra en la etiqueta (LIKE con parámetro escapado)."""
        term = text.strip()
        escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        stmt = select(CpcCode)
        if term.isdigit():
            stmt = stmt.where(CpcCode.code9.like(f"{escaped}%", escape="\\"))
        else:
            stmt = stmt.where(CpcCode.label.ilike(f"%{escaped}%", escape="\\"))
        stmt = stmt.order_by(CpcCode.n_items.desc(), CpcCode.code9).limit(limit)
        return [_entry(r) for r in self.session.scalars(stmt)]

    def count(self) -> int:
        return int(self.session.scalar(select(func.count()).select_from(CpcCode)) or 0)

    def replace_all(self, rows: Sequence[dict[str, object]]) -> int:
        self.session.query(CpcCode).delete()
        self.session.add_all(CpcCode(**r) for r in rows)
        self.session.commit()
        return len(rows)


class DatasetVersionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_or_create(
        self, dataset_hash: str, config_hash: str, rows: dict[str, int], license_name: str
    ) -> DatasetVersion:
        found = self.session.scalar(
            select(DatasetVersion).where(DatasetVersion.dataset_hash == dataset_hash)
        )
        if found:
            return found
        version = DatasetVersion(
            dataset_hash=dataset_hash,
            config_hash=config_hash,
            created_at=datetime.now(UTC),
            train_rows=rows["train"],
            val_rows=rows["val"],
            test_rows=rows["test"],
            license=license_name,
        )
        self.session.add(version)
        self.session.commit()
        return version


class GoldRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_candidates(self, version_id: int, rows: Sequence[dict[str, str]]) -> int:
        existing = set(
            self.session.scalars(
                select(GoldItem.desc_norm).where(GoldItem.dataset_version_id == version_id)
            )
        )
        new = [
            GoldItem(dataset_version_id=version_id, **r)
            for r in rows
            if r["desc_norm"] not in existing
        ]
        self.session.add_all(new)
        self.session.commit()
        return len(new)

    def pending(self, version_id: int) -> list[GoldItem]:
        stmt = (
            select(GoldItem)
            .where(GoldItem.dataset_version_id == version_id, GoldItem.status == "pending")
            .order_by(GoldItem.id)
        )
        return list(self.session.scalars(stmt))

    def review(
        self, item: GoldItem, status: str, gold_code9: str | None, reviewer: str, notes: str = ""
    ) -> None:
        item.status = status
        item.gold_code9 = gold_code9
        item.reviewer = reviewer
        item.notes = notes
        item.reviewed_at = datetime.now(UTC)
        self.session.commit()

    def reviewed(self, version_id: int) -> list[GoldItem]:
        stmt = select(GoldItem).where(
            GoldItem.dataset_version_id == version_id,
            GoldItem.status.in_(("confirmed", "corrected")),
        )
        return list(self.session.scalars(stmt.order_by(GoldItem.id)))

    def all(self, version_id: int) -> list[GoldItem]:
        stmt = (
            select(GoldItem).where(GoldItem.dataset_version_id == version_id).order_by(GoldItem.id)
        )
        return list(self.session.scalars(stmt))


def _entry(row: CpcCode) -> CatalogEntry:
    return CatalogEntry(code9=row.code9, code5=row.code5, label=row.label, n_items=row.n_items)
