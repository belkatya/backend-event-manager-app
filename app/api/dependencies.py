# app/api/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Optional
from db.models import User
from config import settings
import re

# Две схемы безопасности
security_required = HTTPBearer()  # Для обязательной аутентификации
security_optional = HTTPBearer(auto_error=False)  # Для опциональной аутентификации


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security_required)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_iss": False, "verify_aud": False}
        )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await User.get_or_none(email=email)
    if user is None:
        raise credentials_exception

    return user


async def get_current_user_optional(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional)
) -> Optional[User]:
    if credentials is None:
        return None

    try:
        token = credentials.credentials
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_iss": False, "verify_aud": False}  # Добавьте эту строку
        )
        email: str = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None

    user = await User.get_or_none(email=email)
    return user