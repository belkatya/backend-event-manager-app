# app/config/__init__.py
"""
Конфигурация приложения.
Объединяет все настройки в одном месте.
"""

from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from jose import jwt
from passlib.context import CryptContext
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Константы
ROOT_DIR = Path(__file__).parents[2]
ENV_FILE_PATH = ROOT_DIR.joinpath('.env')

# Контекст для хеширования паролей
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
    bcrypt__ident="2b"  # Явно указываем идентификатор
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Environment
    ENV: str = Field(default="development")

    # Database
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432)
    POSTGRES_USER: str = Field(default="postgres")
    POSTGRES_PASSWORD: str = Field(default="postgres")
    POSTGRES_DB: str = Field(default="event_manager")

    # JWT
    SECRET_KEY: str = Field(default="your-secret-key-change-this-in-production")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440)  # 24 hours

    # CORS
    CORS_ORIGINS: List[str] = Field(default=["*"])
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    CORS_ALLOW_METHODS: List[str] = Field(default=["*"])
    CORS_ALLOW_HEADERS: List[str] = Field(default=["*"])

    # API Docs
    DOCS_URL: str = Field(default="/docs")
    REDOC_URL: str = Field(default="/redoc")

    # Server Settings
    RELOAD: bool = Field(default=True)
    WORKERS: int = Field(default=1)

    # Sentry
    USE_SENTRY: bool = Field(default=False)

    # Test
    TEST_DB_URL: str = Field(default="sqlite://:memory:")

    # Computed properties
    @property
    def is_production(self) -> bool:
        return self.ENV.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.ENV.lower() == "development"

    @property
    def postgres_dsn(self) -> str:
        return f"postgres://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def tortoise_config(self) -> dict:
        return {
            "connections": {
                "default": self.postgres_dsn
            },
            "apps": {
                "server": {
                    "models": [
                        "aerich.models",
                        "db.models",
                    ],
                    "default_connection": "default",
                }
            }
        }


# Создаем экземпляр настроек
settings = Settings()
tortoise_settings = settings.tortoise_config


# Функции безопасности (из security.py)
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет соответствие обычного пароля хешированному."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Генерирует хеш пароля."""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Создает JWT токен доступа."""
    if "sub" not in data:
        raise ValueError("Token data must contain 'sub' key")

    to_encode = data.copy()

    # Устанавливаем время истечения
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # Добавляем стандартные поля JWT
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "iss": "event_manager_api",
        "aud": "event_manager_api_users"
    })

    # Кодируем токен
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def create_user_access_token(user) -> str:
    """Создает токен доступа для пользователя."""
    from db.models import User

    if not isinstance(user, User):
        raise TypeError(f"Expected User instance, got {type(user).__name__}")

    if not hasattr(user, 'email') or not user.email:
        raise ValueError("User must have an email address")

    return create_access_token({"sub": user.email})


def decode_token(token: str) -> Dict[str, Any]:
    """Декодирует JWT токен."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise jwt.JWTError("Token has expired")
    except jwt.JWTError:
        raise jwt.JWTError("Could not validate token")


def is_token_expired(token: str) -> bool:
    """Проверяет, истек ли срок действия токена."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False}
        )
        exp_timestamp = payload.get("exp")
        if not exp_timestamp:
            return True

        exp_datetime = datetime.fromtimestamp(exp_timestamp)
        return datetime.utcnow() > exp_datetime
    except jwt.JWTError:
        return True


def get_email_from_token(token: str) -> Optional[str]:
    """Извлекает email из токена без проверки подписи."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_signature": False, "verify_exp": False}
        )
        return payload.get("sub")
    except jwt.JWTError:
        return None


# Алиасы для обратной совместимости
create_access_token_for_user = create_user_access_token

# Экспортируем всё необходимое
__all__ = [
    'settings',
    'tortoise_settings',
    'verify_password',
    'get_password_hash',
    'create_access_token',
    'create_user_access_token',
    'decode_token',
    'is_token_expired',
    'get_email_from_token',
    'create_access_token_for_user',
]