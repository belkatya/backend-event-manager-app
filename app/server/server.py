# app/server/server.py
"""
Основной файл FastAPI приложения.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination
from tortoise import Tortoise
from tortoise.exceptions import DBConnectionError

from config import settings, tortoise_settings

# Импортируем роутеры
from api import router as api_router


def _init_middleware(_app: FastAPI) -> None:
    """
    Инициализация middleware приложения.
    """
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )


def _init_sentry() -> None:
    """
    Инициализация Sentry для мониторинга ошибок.
    """
    if settings.USE_SENTRY:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN if hasattr(settings, 'SENTRY_DSN') else '',
            integrations=[FastApiIntegration()],
            traces_sample_rate=1.0,
            environment=settings.ENV,
        )


async def _init_tortoise(testing: bool = False) -> None:
    """
    Инициализация Tortoise ORM.

    Args:
        testing: Если True, используется тестовая база данных
    """
    if testing:
        # Конфигурация для тестов
        config = {
            "connections": {
                "default": settings.TEST_DB_URL
            },
            "apps": {
                "server": {
                    "models": ["app.db.models"],  # Изменено с "db.models"
                    "default_connection": "default",
                }
            }
        }
    else:
        # Используем конфигурацию из настроек
        config = tortoise_settings

    try:
        # Инициализируем Tortoise
        await Tortoise.init(config=config)

        # Создаем схемы (только при необходимости, например, в dev окружении)
        if settings.is_development and not testing:
            await Tortoise.generate_schemas(safe=True)
            print("Database schemas generated")

        print(f"Database initialized successfully (testing={testing})")

    except Exception as e:
        print(f"Failed to initialize database: {e}")
        raise


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Контекстный менеджер жизненного цикла приложения.
    Управляет подключением к БД.
    """
    testing = getattr(_app.state, "testing", False)

    try:
        # Инициализация базы данных
        await _init_tortoise(testing=testing)

        print("Application startup completed successfully")
        yield

    except Exception as e:
        # Логируем ошибку инициализации
        print(f"Error during app initialization: {e}")
        raise

    finally:
        # Гарантируем закрытие соединений при завершении
        try:
            await Tortoise.close_connections()
            print("Database connections closed")
        except Exception as e:
            print(f"Error closing database connections: {e}")


def create_app(testing: bool = False) -> FastAPI:
    """
    Создает и настраивает экземпляр FastAPI приложения.

    Args:
        testing: Если True, создается приложение для тестов

    Returns:
        FastAPI: Настроенное приложение
    """
    # Инициализация Sentry (если включено)
    _init_sentry()

    # Создаем приложение с lifespan
    _app = FastAPI(
        title="Wevent API",
        description="API приложения для организации мероприятий",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=settings.DOCS_URL if settings.is_development else None,
        redoc_url=settings.REDOC_URL if settings.is_development else None,
    )

    # Устанавливаем флаг тестирования в состояние приложения
    _app.state.testing = testing

    # Инициализация middleware
    _init_middleware(_app)

    # Подключаем роутеры
    _app.include_router(api_router)
    add_pagination(_app)

    # Корневые endpoint'ы
    @_app.get("/")
    async def root():
        """
        Корневой endpoint для проверки работы API.

        Returns:
            dict: Сообщение о статусе API
        """
        return {
            "message": "Wevent API",
            "version": "1.0.0",
            "status": "running",
            "environment": settings.ENV,
            "docs": f"{settings.DOCS_URL}" if settings.DOCS_URL else "disabled"
        }

    @_app.get("/health")
    async def health_check():
        """
        Endpoint для проверки здоровья приложения.

        Returns:
            dict: Статус здоровья приложения
        """
        try:
            # Проверяем соединение с БД
            conn = Tortoise.get_connection("default")
            # Выполняем простой запрос для проверки соединения
            await conn.execute_query("SELECT 1")
            db_status = "connected"
        except DBConnectionError:
            db_status = "disconnected"
        except Exception as e:
            db_status = f"error: {str(e)}"

        return {
            "status": "healthy" if db_status == "connected" else "unhealthy",
            "database": db_status,
            "environment": settings.ENV,
            "timestamp": datetime.now().isoformat()
        }

    return _app


# Создаем экземпляр приложения для production
app = create_app()


# Экспортируем для использования в main.py
__all__ = ['app', 'create_app']