"""SQLAlchemy models for BUS Core domain data."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Generator

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker


def _resolve_db_path() -> Path:
    """Resolve the SQLite database path with launcher-aware defaults."""

    if getattr(sys, "frozen", False):  # running from the packaged launcher
        base = Path(os.environ.get("LOCALAPPDATA", "./data")) / "BUSCore"
    else:
        base = Path("./data")
    base.mkdir(parents=True, exist_ok=True)
    return (base / "app.db").resolve()


DB_PATH = _resolve_db_path()
ENGINE = create_engine(
    f"sqlite:///{DB_PATH.as_posix()}", connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=ENGINE)

Base = declarative_base()


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    contact = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    sku = Column(String, nullable=True)
    name = Column(String, nullable=False)
    qty = Column(Float, nullable=False, server_default="0")
    unit = Column(String, nullable=True)
    price = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=True)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, server_default="pending")
    due = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)
    reader_id = Column(String, nullable=False)
    label = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


Base.metadata.create_all(ENGINE)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = [
    "Attachment",
    "Base",
    "ENGINE",
    "Item",
    "SessionLocal",
    "Task",
    "Vendor",
    "get_session",
]
