# app/models/events.py
"""
Pydantic модели для событий.
"""

from datetime import date, time, datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict

from .user import BaseUser
from .location import BaseLocation
from .category import BaseCategory


class EventBase(BaseModel):
    """Базовая схема события"""
    title: str = Field(..., min_length=2, max_length=255)
    short_description: str
    full_description: str
    date: date
    time: time
    location_id: int
    category_ids: List[int] = Field(..., min_items=1)


class EventCreate(EventBase):
    """Схема для создания события"""

    @field_validator('date')
    @classmethod
    def validate_future_date(cls, v: date) -> date:
        """Проверка, что дата события в будущем"""
        if v < date.today():
            raise ValueError('Event date must be in the future')
        return v


class EventUpdate(BaseModel):
    """Схема для обновления события"""
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    short_description: Optional[str] = None
    full_description: Optional[str] = None
    date: Optional[date] = None
    time: Optional[time] = None
    location_id: Optional[int] = None
    category_ids: Optional[List[int]] = None

    @field_validator('date')
    @classmethod
    def validate_future_date(cls, v: Optional[date]) -> Optional[date]:
        """Проверка, что дата события в будущем"""
        if v is not None and v < date.today():
            raise ValueError('Event date must be in the future')
        return v

    @field_validator('category_ids')
    @classmethod
    def validate_categories(cls, v: Optional[List[int]]) -> Optional[List[int]]:
        """Проверка, что есть хотя бы одна категория"""
        if v is not None and len(v) < 1:
            raise ValueError('Event must have at least one category')
        return v


class EventInDB(BaseModel):
    """Схема события из БД"""
    id: int
    title: str
    short_description: str
    full_description: str
    date: date
    time: time
    location: BaseLocation
    categories: List[BaseCategory]
    organizer: BaseUser
    likes_count: int = Field(ge=0, default=0)
    participants_count: int = Field(ge=0, default=0)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventResponse(EventInDB):
    """Публичный ответ с данными события"""
    pass


class EventWithUserStatus(EventResponse):
    """Событие со статусом пользователя (лайк/регистрация)"""
    is_liked: bool = Field(default=False)
    is_registered: bool = Field(default=False)


class EventFilterParams(BaseModel):
    """Параметры фильтрации событий"""
    category_id: Optional[int] = None
    city: Optional[str] = None
    search: Optional[str] = None
    sort_by_likes: Optional[str] = None
    page: int = 1
    size: int = Field(ge=1, le=100, default=20)


class EventListResponse(BaseModel):
    """Список событий (для пагинации)"""
    items: List[EventResponse]
    total: int
    page: int
    size: int
    pages: int


# Алиасы для обратной совместимости
BaseEvent = EventResponse  # Для совместимости с существующим кодом
PaginatedResponse = EventListResponse  # Для совместимости с существующим кодом