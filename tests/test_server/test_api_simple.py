import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.server.server import create_app
from tortoise import Tortoise


@pytest_asyncio.fixture(scope="function")
async def async_client():
    """Фикстура для асинхронного тестового клиента."""
    app = create_app(testing=True)

    # Инициализируем базу данных
    db_url = "sqlite://:memory:"
    config = {
        "connections": {"default": db_url},
        "apps": {
            "server": {
                "models": ["app.db.models"],
                "default_connection": "default",
            }
        }
    }

    await Tortoise.init(config=config)
    await Tortoise.generate_schemas()

    async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
    ) as client:
        yield client

    # Очистка
    await Tortoise.close_connections()


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient):
    """Тест проверки здоровья приложения."""
    response = await async_client.get("/health")

    print(f"Health check status: {response.status_code}")
    print(f"Health check response: {response.json()}")

    assert response.status_code == 200
    assert "status" in response.json()


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    """Тест корневого endpoint."""
    response = await async_client.get("/")

    print(f"Root endpoint status: {response.status_code}")
    print(f"Root endpoint response: {response.json()}")

    assert response.status_code == 200
    assert "message" in response.json()
    assert "Wevent API" in response.json()["message"]  # Исправлено


@pytest.mark.asyncio
async def test_get_all_locations_empty(async_client: AsyncClient):
    """Тест получения пустого списка локаций."""
    response = await async_client.get("/api/locations/")

    print(f"Locations endpoint status: {response.status_code}")
    print(f"Locations endpoint response: {response.json()}")

    assert response.status_code == 200
    data = response.json()

    # Может быть список или пагинация
    if isinstance(data, dict) and 'items' in data:
        locations = data['items']
    else:
        locations = data

    assert isinstance(locations, list)
    assert len(locations) == 0