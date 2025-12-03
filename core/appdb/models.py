# SPDX-License-Identifier: AGPL-3.0-or-later
"""Application database models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Vendor(Base):
    __tablename__ = "vendors"
    __table_args__ = (UniqueConstraint("name", name="uq_vendors_name"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    contact = Column(String, nullable=True)
    role = Column(String, nullable=False, server_default="contact")  # compat: derived from is_vendor
    # Flags
    is_vendor = Column(Integer, nullable=False, server_default="0")  # 0/1 (SQLite boolean)
    is_org = Column(Integer, nullable=True, default=None)  # 0/1 (SQLite boolean); NULL allowed
    organization_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    meta = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    organization = relationship("Vendor", remote_side=[id], uselist=False)


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    sku = Column(String, nullable=True)
    name = Column(String, nullable=False)
    uom = Column(String, nullable=False, default="ea")          # 'ea','g','mm','mm2','mm3'
    qty_stored = Column(Integer, nullable=False, default=0)      # canonical on-hand
    price = Column(Float, default=0)
    notes = Column(Text, nullable=True)
    item_type = Column(String, nullable=True)
    location = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    notes = Column(Text)
    items = relationship("RecipeItem", back_populates="recipe", cascade="all, delete-orphan")


class RecipeItem(Base):
    __tablename__ = "recipe_items"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    role = Column(String, nullable=False)
    qty_stored = Column(Integer, nullable=False)

    recipe = relationship("Recipe", back_populates="items")
    item = relationship("Item")


__all__ = [
    "Base",
    "Item",
    "Recipe",
    "RecipeItem",
    "Vendor",
]
