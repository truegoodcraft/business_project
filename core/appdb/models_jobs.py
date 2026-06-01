# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func as sa_func

from core.appdb.models import Base


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "status in ('draft','active','blocked','ready','done','cancelled')",
            name="ck_jobs_status",
        ),
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_contact_id", "contact_id"),
        Index("ix_jobs_due_date", "due_date"),
    )

    id = Column(Integer, primary_key=True)
    contact_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="draft", server_default="draft")
    priority = Column(Integer, nullable=False, default=0, server_default="0")
    due_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=sa_func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=sa_func.now(), onupdate=sa_func.now(), nullable=False)
    closed_at = Column(DateTime, nullable=True)

    contact = relationship("Vendor")
    lines = relationship("JobLine", back_populates="job", cascade="all, delete-orphan")
    events = relationship("JobEvent", back_populates="job", cascade="all, delete-orphan")


class JobLine(Base):
    __tablename__ = "job_lines"
    __table_args__ = (
        CheckConstraint(
            "line_type in ('product','service','fee','note')",
            name="ck_job_lines_line_type",
        ),
        CheckConstraint(
            "status in ('pending','produced','delivered','cancelled')",
            name="ck_job_lines_status",
        ),
    )

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=True)
    line_type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    qty_base = Column(Integer, nullable=True)
    display_uom = Column(String, nullable=True)
    unit_price_cents = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default="pending", server_default="pending")
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime, server_default=sa_func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=sa_func.now(), onupdate=sa_func.now(), nullable=False)

    job = relationship("Job", back_populates="lines")
    item = relationship("Item")
    recipe = relationship("Recipe")


class JobEvent(Base):
    __tablename__ = "job_events"
    __table_args__ = (Index("ix_job_events_created_at", "created_at"),)

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    source_kind = Column(String, nullable=True)
    source_id = Column(String, nullable=True)
    meta = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=sa_func.now(), nullable=False)

    job = relationship("Job", back_populates="events")


__all__ = ["Job", "JobLine", "JobEvent"]
