# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func as sa_func

from core.appdb.models import Base


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint("status in ('draft','issued','paid','void')", name="ck_invoices_status"),
        Index("ix_invoices_contact_id", "contact_id"),
        Index("ix_invoices_job_id", "job_id"),
        Index("ix_invoices_status", "status"),
        Index("ix_invoices_issue_date", "issue_date"),
        Index("ix_invoices_due_date", "due_date"),
    )

    id = Column(Integer, primary_key=True)
    invoice_number = Column(String, nullable=False, unique=True, index=True)
    contact_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    status = Column(String, nullable=False, default="draft", server_default="draft")
    issue_date = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    voided_at = Column(DateTime, nullable=True)
    tax_rate_basis_points = Column(Integer, nullable=False, default=0, server_default="0")
    subtotal_cents = Column(Integer, nullable=False, default=0, server_default="0")
    tax_cents = Column(Integer, nullable=False, default=0, server_default="0")
    total_cents = Column(Integer, nullable=False, default=0, server_default="0")
    paid_cash_event_id = Column(Integer, ForeignKey("cash_events.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=sa_func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=sa_func.now(), onupdate=sa_func.now(), nullable=False)

    contact = relationship("Vendor")
    job = relationship("Job")
    paid_cash_event = relationship("CashEvent")
    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"
    __table_args__ = (
        CheckConstraint("line_type in ('product','service','fee','note')", name="ck_invoice_lines_line_type"),
        Index("ix_invoice_lines_invoice_id", "invoice_id"),
        Index("ix_invoice_lines_job_line_id", "job_line_id"),
    )

    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    job_line_id = Column(Integer, ForeignKey("job_lines.id"), nullable=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=True)
    line_type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    quantity_decimal = Column(String, nullable=True)
    uom = Column(String, nullable=True)
    unit_price_cents = Column(Integer, nullable=True)
    taxable = Column(Boolean, nullable=False, default=True, server_default="1")
    line_subtotal_cents = Column(Integer, nullable=False, default=0, server_default="0")
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime, server_default=sa_func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=sa_func.now(), onupdate=sa_func.now(), nullable=False)

    invoice = relationship("Invoice", back_populates="lines")
    job_line = relationship("JobLine")
    item = relationship("Item")


class DocumentSequence(Base):
    __tablename__ = "document_sequences"

    key = Column(String, primary_key=True)
    next_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=sa_func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=sa_func.now(), onupdate=sa_func.now(), nullable=False)


__all__ = ["Invoice", "InvoiceLine", "DocumentSequence"]
