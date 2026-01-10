# app/services/auth.py
"""
Сервис для работы с аутентификацией и пользователями.
Содержит бизнес-логику для регистрации, входа и управления пользователями.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext

from db.models import User
from models.user import UserCreate, TokenPayload, LoginRequest
from models.auth import TokenResponse, AuthError
from config import settings
from api.exceptions import AuthException, BadRequestException


class AuthService:
    """Сервис аутентификации"""

    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Проверяет соответствие пароля его хешу.

        Args:
            plain_password: Обычный пароль
            hashed_password: Хешированный пароль из БД

        Returns:
            bool: True если пароль верный
        """
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """
        Генерирует хеш пароля.

        Args:
            password: Пароль для хеширования

        Returns:
            str: Хешированный пароль
        """
        return self.pwd_context.hash(password)

    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Создает JWT токен.

        Args:
            data: Данные для включения в токен
            expires_delta: Время жизни токена

        Returns:
            str: JWT токен
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "iss": getattr(settings, 'PROJECT_NAME', 'event_app'),
            "aud": getattr(settings, 'API_V1_STR', '/api')
        })

        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        return encoded_jwt

    def create_user_access_token(self, user: User) -> str:
        """
        Создает токен доступа для пользователя.

        Args:
            user: Объект пользователя

        Returns:
            str: JWT токен
        """
        return self.create_access_token(data={"sub": user.email})

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Аутентифицирует пользователя по email и паролю.

        Args:
            email: Email пользователя
            password: Пароль пользователя

        Returns:
            Optional[User]: Объект пользователя или None
        """
        user = await User.get_or_none(email=email)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    async def register_user(self, user_data: UserCreate) -> User:
        """
        Регистрирует нового пользователя.

        Args:
            user_data: Данные для регистрации

        Returns:
            User: Созданный пользователь

        Raises:
            BadRequestException: Если пользователь уже существует
        """
        # Проверяем, существует ли пользователь
        existing_user = await User.get_or_none(email=user_data.email)
        if existing_user:
            raise BadRequestException("User with this email already exists")

        # Хешируем пароль
        hashed_password = self.get_password_hash(user_data.password)

        # Создаем пользователя
        user = await User.create(
            email=user_data.email,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            hashed_password=hashed_password,
        )

        return user

    async def change_password(self, user: User, old_password: str, new_password: str) -> None:
        """
        Изменяет пароль пользователя.

        Args:
            user: Объект пользователя
            old_password: Старый пароль
            new_password: Новый пароль

        Raises:
            BadRequestException: Если старый пароль неверен или новый пароль совпадает со старым
        """
        # Проверяем старый пароль
        if not self.verify_password(old_password, user.hashed_password):
            raise BadRequestException("Incorrect old password")

        # Проверяем, что новый пароль отличается от старого
        if self.verify_password(new_password, user.hashed_password):
            raise BadRequestException("New password must be different from old password")

        # Хешируем новый пароль
        user.hashed_password = self.get_password_hash(new_password)
        await user.save()

    def decode_token(self, token: str) -> TokenPayload:
        """
        Декодирует JWT токен.

        Args:
            token: JWT токен

        Returns:
            TokenPayload: Декодированные данные

        Raises:
            AuthException: Если токен невалиден
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            email: str = payload.get("sub")
            exp: int = payload.get("exp")
            iat: int = payload.get("iat")
            iss: str = payload.get("iss")
            aud: str = payload.get("aud")

            if email is None:
                raise AuthException("Invalid token")

            return TokenPayload(
                sub=email,
                exp=datetime.fromtimestamp(exp) if exp else None,
                iat=datetime.fromtimestamp(iat) if iat else None,
                iss=iss,
                aud=aud
            )
        except JWTError as e:
            raise AuthException(f"Could not validate credentials: {str(e)}")

    def create_token_response(self, user: User) -> TokenResponse:
        """
        Создает ответ с токеном и данными пользователя.

        Args:
            user: Объект пользователя

        Returns:
            TokenResponse: Ответ с токеном
        """
        access_token = self.create_user_access_token(user)

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Получает пользователя по email.

        Args:
            email: Email пользователя

        Returns:
            Optional[User]: Объект пользователя или None
        """
        return await User.get_or_none(email=email)

    async def update_user_profile(self, user: User, update_data: Dict[str, Any]) -> User:
        """
        Обновляет профиль пользователя.

        Args:
            user: Объект пользователя
            update_data: Данные для обновления

        Returns:
            User: Обновленный пользователь
        """
        # Удаляем None значения и пустые поля
        clean_data = {k: v for k, v in update_data.items() if v is not None}

        if not clean_data:
            return user

        # Обновляем поля
        for field, value in clean_data.items():
            if hasattr(user, field):
                setattr(user, field, value)

        await user.save()
        await user.refresh_from_db()
        return user


# Экземпляр сервиса для использования
auth_service = AuthService()