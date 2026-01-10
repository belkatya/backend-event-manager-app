import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator

from httpx import AsyncClient, ASGITransport
from tortoise import Tortoise

from app.server.server import create_app


@pytest.fixture(scope="session")
def event_loop():
    """Создание events loop для тестов с областью видимости сессии."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_db():
    """Инициализация тестовой базы данных перед всеми тестами."""
    # Используем SQLite в памяти для тестов
    db_url = "sqlite://:memory:"

    # Правильная конфигурация Tortoise - должна совпадать с моделями
    config = {
        "connections": {
            "default": db_url
        },
        "apps": {
            "server": {  # Должно быть "server" как в моделях
                "models": ["app.db.models"],  # Путь к моделям
                "default_connection": "default",
            }
        }
    }

    # Инициализация Tortoise
    await Tortoise.init(config=config)

    # Создание таблиц
    await Tortoise.generate_schemas()

    yield

    # Закрытие соединений
    await Tortoise.close_connections()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_db():
    """
    Фикстура для очистки базы данных перед каждым тестом.
    """
    yield  # Сначала выполняем тест

    # Очищаем после теста
    try:
        for model in Tortoise.apps.get("server", {}).values():
            await model.all().delete()
    except Exception:
        pass  # Игнорируем ошибки при очистке


@pytest_asyncio.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Фикстура для асинхронного тестового клиента."""
    app = create_app(testing=True)

    # Используем ASGITransport для подключения к FastAPI приложению
    async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
    ) as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def auth_token(async_client: AsyncClient):
    """Фикстура для получения токена аутентификации."""
    # Сначала регистрируем пользователя
    register_data = {
        "email": "test@example.com",
        "first_name": "Тест",
        "last_name": "Пользователь",
        "password": "TestPass123!",
    }

    response = await async_client.post("/api/auth/register", json=register_data)

    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        # Если регистрация не удалась, возможно пользователь уже существует
        # Попробуем логин
        login_data = {
            "username": "test@example.com",
            "password": "TestPass123!"
        }
        response = await async_client.post("/api/auth/login", json=login_data)
        return response.json()["access_token"]