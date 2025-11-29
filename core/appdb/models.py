# SPDX-License-Identifier: AGPL-3.0-or-later
"""Application database models."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Vendor(Base):
    __tablename__ = "vendors"
    __table_args__ = (UniqueConstraint("name", name="uq_vendors_name"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    contact = Column(String, nullable=True)
    role = Column(String, nullable=False, server_default="vendor")  # vendor|contact|both
    kind = Column(String, nullable=False, server_default="org")  # org|person
    organization_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    meta = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    organization = relationship("Vendor", remote_side=[id], uselist=False)


__all__ = ["Base", "Vendor"]
