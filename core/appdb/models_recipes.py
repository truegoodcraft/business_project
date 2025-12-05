# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from core.appdb.models import Base


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=True, unique=True)
    output_item_id = Column(Integer, ForeignKey("items.id"), nullable=True)
    output_qty = Column(Float, nullable=False, default=1.0)
    is_archived = Column(Boolean, nullable=False, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    items = relationship("RecipeItem", back_populates="recipe", cascade="all, delete-orphan")


class RecipeItem(Base):
    __tablename__ = "recipe_items"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    qty_required = Column(Float, nullable=False)
    is_optional = Column(Boolean, nullable=False, default=False)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    recipe = relationship("Recipe", back_populates="items")


class ManufacturingRun(Base):
    __tablename__ = "manufacturing_runs"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=True)
    output_item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    output_qty = Column(Float, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    executed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    meta = Column(Text, nullable=True)
