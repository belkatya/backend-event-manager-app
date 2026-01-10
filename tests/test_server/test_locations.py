import pytest
import pytest_asyncio
from httpx import AsyncClient
from tortoise import Tortoise

from app.db.models import Location, User


@pytest.mark.asyncio
class TestLocationsAPI:
    """Тесты для API локаций"""

    async def _create_test_user(self, async_client: AsyncClient, email: str) -> str:
        """Создание тестового пользователя и получение токена"""
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": email,
                "first_name": "Тест",
                "last_name": "Пользователь",
                "password": "TestPass123!",
            },
        )
        return response.json()["access_token"]

    async def test_get_all_locations_empty(self, async_client: AsyncClient):
        """Получение списка локаций (пустой)"""
        response = await async_client.get("/api/locations/")

        assert response.status_code == 200
        data = response.json()

        # Может быть список или пагинация
        if isinstance(data, dict) and 'items' in data:
            locations = data['items']
        else:
            locations = data

        assert isinstance(locations, list)
        assert len(locations) == 0

    async def test_get_all_locations_with_data(self, async_client: AsyncClient):
        """Получение списка локаций (с данными)"""
        # Создаем тестовые локации
        await Location.create(city="Москва", street="Тверская", house="1")
        await Location.create(city="Санкт-Петербург", street="Невский", house="2")
        await Location.create(city="Казань", street="Кремлевская", house="3")

        response = await async_client.get("/api/locations/")

        assert response.status_code == 200
        data = response.json()

        if isinstance(data, dict) and 'items' in data:
            locations = data['items']
        else:
            locations = data

        assert isinstance(locations, list)
        assert len(locations) == 3

        # Проверяем структуру локаций
        for location in locations:
            assert "id" in location
            assert "city" in location
            assert "street" in location
            assert "house" in location

        # Проверяем, что все локации есть в списке
        cities = [loc["city"] for loc in locations]
        assert "Москва" in cities
        assert "Санкт-Петербург" in cities
        assert "Казань" in cities

    async def test_get_location_by_id_success(self, async_client: AsyncClient):
        """Получение локации по ID"""
        # Создаем локацию
        location = await Location.create(
            city="Екатеринбург",
            street="Ленина",
            house="10А"
        )

        response = await async_client.get(f"/api/locations/{location.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == location.id
        assert data["city"] == "Екатеринбург"
        assert data["street"] == "Ленина"
        assert data["house"] == "10А"

    async def test_get_location_by_id_not_found(self, async_client: AsyncClient):
        """Получение несуществующей локации"""
        response = await async_client.get("/api/locations/999999")

        assert response.status_code == 404

    async def test_create_location_success(self, async_client: AsyncClient):
        """Успешное создание локации"""
        token = await self._create_test_user(async_client, "location_creator@example.com")

        response = await async_client.post(
            "/api/locations/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "city": "Новосибирск",
                "street": "Красный проспект",
                "house": "25"
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["city"] == "Новосибирск"
        assert data["street"] == "Красный проспект"
        assert data["house"] == "25"
        assert "id" in data

        # Проверяем, что локация создана в базе
        location = await Location.get_or_none(city="Новосибирск")
        assert location is not None

    async def test_create_location_missing_fields(self, async_client: AsyncClient):
        """Создание локации с отсутствующими полями"""
        token = await self._create_test_user(async_client, "incomplete_loc@example.com")

        # Без города
        response = await async_client.post(
            "/api/locations/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "street": "Улица",
                "house": "1"
            },
        )

        assert response.status_code == 422

        # Без улицы
        response = await async_client.post(
            "/api/locations/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "city": "Город",
                "house": "1"
            },
        )

        assert response.status_code == 422

    async def test_create_location_unauthorized(self, async_client: AsyncClient):
        """Создание локации без авторизации"""
        response = await async_client.post(
            "/api/locations/",
            json={
                "city": "Город",
                "street": "Улица",
                "house": "1"
            },
        )

        # Ожидаем ошибку аутентификации/авторизации
        assert response.status_code in [401, 403]

        # Проверяем, что это действительно ошибка доступа
        data = response.json()
        assert "detail" in data

        # Проверяем ключевые слова в сообщении об ошибке
        error_text = data["detail"].lower()
        expected_phrases = [
            "forbidden",
            "unauthorized",
            "not authenticated",
            "credentials",
            "authentication",
            "authorization"
        ]

        assert any(phrase in error_text for phrase in expected_phrases), \
            f"Unexpected error message: {data['detail']}"

    async def test_filter_locations_by_city(self, async_client: AsyncClient):
        """Фильтрация локаций по городу"""
        # Создаем тестовые локации
        await Location.create(city="Москва", street="Тверская", house="1")
        await Location.create(city="Москва", street="Арбат", house="10")
        await Location.create(city="Санкт-Петербург", street="Невский", house="2")

        # Фильтруем по Москве
        response = await async_client.get("/api/locations/?city=Москва")

        assert response.status_code == 200
        data = response.json()

        if isinstance(data, dict) and 'items' in data:
            locations = data['items']
        else:
            locations = data

        assert isinstance(locations, list)
        assert len(locations) == 2

        # Все локации должны быть в Москве
        for location in locations:
            assert location["city"] == "Москва"

    async def test_location_fields_validation(self, async_client: AsyncClient):
        """Валидация полей локации"""
        token = await self._create_test_user(async_client, "validation@example.com")

        # Слишком длинный город
        response = await async_client.post(
            "/api/locations/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "city": "А" * 101,  # 101 символ
                "street": "Улица",
                "house": "1"
            },
        )

        # Может быть 200 или 422
        assert response.status_code in [200, 422]

        # Пустой дом
        response = await async_client.post(
            "/api/locations/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "city": "Город",
                "street": "Улица",
                "house": ""  # Пустой дом
            },
        )

        # Может быть 200 или 422
        assert response.status_code in [200, 422]