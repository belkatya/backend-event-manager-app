# app/api/schemas.py
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict, constr
from datetime import date, time, datetime
from typing import List, Optional
from fastapi_pagination import Page
from datetime import date as date_type, time as time_type

# Base schemas
class BaseUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    created_at: datetime
    updated_at: datetime


class BaseCategory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str = Field(..., min_length=1, max_length=100)


class BaseLocation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    city: str = Field(..., min_length=1, max_length=100)
    street: str = Field(..., min_length=1, max_length=255)
    house: str = Field(..., min_length=1, max_length=50)


class BaseEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str = Field(..., min_length=2, max_length=255)
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


# Схемы для статусов пользователя (добавлено)
class EventWithUserStatus(BaseEvent):
    """Событие со статусом пользователя (лайк/регистрация)"""
    is_liked: bool = Field(default=False)
    is_registered: bool = Field(default=False)


class PaginatedEventsWithStatus(BaseModel):
    """Пагинированный ответ со статусами пользователя"""
    items: List[EventWithUserStatus]
    total: int
    page: int
    size: int
    pages: int


class UserWithStats(BaseUser):
    """Пользователь со статистикой по событиям"""
    liked_events_count: int = Field(default=0, ge=0)
    registered_events_count: int = Field(default=0, ge=0)
    organized_events_count: int = Field(default=0, ge=0)


# Request schemas
class UserRegister(BaseModel):
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8)

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c.isalpha() for c in v):
            raise ValueError('Password must contain at least one letter')
        return v


class UserLogin(BaseModel):
    username: EmailStr
    password: str


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c.isalpha() for c in v):
            raise ValueError('Password must contain at least one letter')
        return v


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class LocationCreate(BaseModel):
    city: str = Field(..., min_length=1, max_length=100)
    street: str = Field(..., min_length=1, max_length=255)
    house: str = Field(..., min_length=1, max_length=50)


class EventCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    short_description: str
    full_description: str
    date: date
    time: time
    location_id: int
    category_ids: List[int] = Field(..., min_length=1)

    @field_validator('date')
    @classmethod
    def validate_future_date(cls, v: date) -> date:
        if v < date.today():
            raise ValueError('Event date must be in the future')
        return v


class EventUpdate(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    title: Optional[str] = Field(None, min_length=2, max_length=255)
    short_description: Optional[str] = None
    full_description: Optional[str] = None
    date: Optional[date_type] = None  # Используем date_type
    time: Optional[time_type] = None  # Используем time_type
    location_id: Optional[int] = None
    category_ids: Optional[List[int]] = None

    @field_validator('date')
    @classmethod
    def validate_future_date(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v < date.today():
            raise ValueError('Event date must be in the future')
        return v

    @field_validator('category_ids')
    @classmethod
    def validate_categories(cls, v: Optional[List[int]]) -> Optional[List[int]]:
        if v is not None and len(v) < 1:
            raise ValueError('Event must have at least one category')
        return v


# Response schemas
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    message: str


# Query params
class EventFilterParams(BaseModel):
    category_id: Optional[int] = None
    city: Optional[str] = None
    search: Optional[str] = None
    sort_by_likes: Optional[constr(pattern="^(asc|desc)$")] = None
    page: int = 1
    size: int = Field(ge=1, le=100, default=20)


class LocationFilterParams(BaseModel):
    city: Optional[str] = None
    page: int = 1
    size: int = Field(ge=1, le=100, default=20)


# Pagination response
class PaginatedResponse(BaseModel):
    items: List[BaseEvent]
    total: int
    page: int
    size: int
    pages: int