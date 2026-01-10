# app/models/location.py
"""
Pydantic модели для локаций.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class LocationBase(BaseModel):
    """Базовая схема локации"""
    city: str = Field(..., min_length=1, max_length=100)
    street: str = Field(..., min_length=1, max_length=255)
    house: str = Field(..., min_length=1, max_length=50)


class LocationCreate(LocationBase):
    """Схема для создания локации"""
    pass


class LocationInDB(LocationBase):
    """Схема локации из БД"""
    id: int

    model_config = ConfigDict(from_attributes=True)


class LocationResponse(LocationInDB):
    """Публичный ответ с данными локации"""
    pass


class LocationFilterParams(BaseModel):
    """Параметры фильтрации локаций"""
    city: Optional[str] = None
    page: int = 1
    size: int = Field(ge=1, le=100, default=20)


class LocationListResponse(BaseModel):
    """Список локаций (для пагинации)"""
    items: List[LocationResponse]
    total: int
    page: int
    size: int
    pages: int

class LocationUpdate(BaseModel):
    """Схема для обновления локации"""
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    street: Optional[str] = Field(None, min_length=1, max_length=255)
    house: Optional[str] = Field(None, min_length=1, max_length=50)


# Алиасы для обратной совместимости
BaseLocation = LocationResponse  # Для совместимости с существующим кодом