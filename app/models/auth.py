# app/models/auth.py
"""
Pydantic модели для аутентификации и токенов.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    """Базовая модель токена"""
    access_token: str
    token_type: str = "bearer"


class TokenResponse(Token):
    """Полный ответ с токеном и данными пользователя"""
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    created_at: datetime
    updated_at: datetime


class AuthResponse(BaseModel):
    """Базовый ответ для аутентификации"""
    message: str


class LoginForm(BaseModel):
    """Форма входа (совместима с OAuth2PasswordRequestForm)"""
    username: EmailStr  # Для совместимости с OAuth2PasswordRequestForm
    password: str


class TokenPayload(BaseModel):
    """Полезная нагрузка JWT токена"""
    sub: str  # email пользователя
    exp: datetime
    iat: datetime
    iss: Optional[str] = None
    aud: Optional[str] = None


class AuthError(BaseModel):
    """Модель ошибки аутентификации"""
    detail: str


class OAuth2PasswordRequestForm(BaseModel):
    """Форма для OAuth2 совместимого входа"""
    username: EmailStr
    password: str
    scope: str = ""
    grant_type: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None


# Алиасы для обратной совместимости
MessageResponse = AuthResponse  # Для совместимости с существующим кодом