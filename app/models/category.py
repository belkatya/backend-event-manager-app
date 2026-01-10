# app/models/category.py
"""
Pydantic модели для категорий.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List


class CategoryBase(BaseModel):
    """Базовая схема категории"""
    name: str = Field(..., min_length=1, max_length=100)


class CategoryCreate(CategoryBase):
    """Схема для создания категории"""
    pass


class CategoryInDB(CategoryBase):
    """Схема категории из БД"""
    id: int

    model_config = ConfigDict(from_attributes=True)


class CategoryResponse(CategoryInDB):
    """Публичный ответ с данными категории"""
    pass


class CategoryListResponse(BaseModel):
    """Список категорий"""
    items: List[CategoryResponse]
    total: int
    page: int
    size: int
    pages: int


# Алиасы для обратной совместимости
BaseCategory = CategoryResponse  # Для совместимости с существующим кодом