# app/models/user.py
"""
Pydantic модели для пользователей.
Эти модели используются для валидации и сериализации данных пользователя.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict


class UserBase(BaseModel):
    """Базовая схема пользователя"""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)


class UserCreate(UserBase):
    """Схема для создания пользователя (регистрация)"""
    password: str = Field(..., min_length=8)

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Валидация пароля"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c.isalpha() for c in v):
            raise ValueError('Password must contain at least one letter')
        return v


class UserUpdate(BaseModel):
    """Схема для обновления пользователя"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None


class UserInDB(UserBase):
    """Схема пользователя из БД (с идентификатором и метками времени)"""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserResponse(UserInDB):
    """Публичный ответ с данными пользователя"""
    pass


class UserWithStats(UserResponse):
    """Пользователь со статистикой по событиям"""
    liked_events_count: Optional[int] = Field(default=0, ge=0)
    registered_events_count: Optional[int] = Field(default=0, ge=0)
    organized_events_count: Optional[int] = Field(default=0, ge=0)


class PasswordChange(BaseModel):
    """Схема для изменения пароля"""
    old_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Валидация нового пароля"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c.isalpha() for c in v):
            raise ValueError('Password must contain at least one letter')
        return v


class LoginRequest(BaseModel):
    """Схема для входа пользователя"""
    email: EmailStr
    password: str


class UserListResponse(BaseModel):
    """Список пользователей (для пагинации)"""
    items: List[UserResponse]
    total: int
    page: int
    size: int
    pages: int


# Алиасы для обратной совместимости
BaseUser = UserResponse  # Для совместимости с существующим кодом
UserRegister = UserCreate  # Для совместимости с существующим кодом