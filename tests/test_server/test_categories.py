# tests/test_server/test_categories.py
import pytest
from httpx import AsyncClient
from db.models import Category, User


@pytest.mark.asyncio
class TestCategoriesAPI:
    """Тесты для API категорий"""

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

    async def test_get_all_categories_empty(self, async_client: AsyncClient):
        """Получение списка категорий (пустой)"""
        response = await async_client.get("/api/categories/")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 0

    async def test_get_all_categories_with_data(self, async_client: AsyncClient):
        """Получение списка категорий (с данными)"""
        # Создаем тестовые категории
        await Category.create(name="Музыка")
        await Category.create(name="Спорт")
        await Category.create(name="Технологии")

        response = await async_client.get("/api/categories/")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 3

        # Проверяем структуру категорий
        for category in data:
            assert "id" in category
            assert "name" in category

        # Проверяем, что все категории есть в списке
        category_names = [cat["name"] for cat in data]
        assert "Музыка" in category_names
        assert "Спорт" in category_names
        assert "Технологии" in category_names

    async def test_create_category_success(self, async_client: AsyncClient):
        """Успешное создание категории"""
        token = await self._create_test_user(async_client, "category_creator@example.com")

        response = await async_client.post(
            "/api/categories/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Новая категория"
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Новая категория"
        assert "id" in data

        # Проверяем, что категория создана в базе
        category = await Category.get_or_none(name="Новая категория")
        assert category is not None

    async def test_create_category_duplicate_name(self, async_client: AsyncClient):
        """Создание категории с существующим именем"""
        token = await self._create_test_user(async_client, "duplicate_cat@example.com")

        # Создаем первую категорию
        await async_client.post(
            "/api/categories/",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Дубликат"},
        )

        # Пытаемся создать категорию с тем же именем
        response = await async_client.post(
            "/api/categories/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Дубликат"  # То же самое имя
            },
        )

        # Должно быть 400 или 409
        assert response.status_code in [400, 409]

    async def test_create_category_empty_name(self, async_client: AsyncClient):
        """Создание категории с пустым названием"""
        token = await self._create_test_user(async_client, "empty_cat@example.com")

        response = await async_client.post(
            "/api/categories/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": ""  # Пустое название
            },
        )

        assert response.status_code == 422

    async def test_create_category_unauthorized(self, async_client: AsyncClient):
        """Создание категории без авторизации"""
        response = await async_client.post(
            "/api/categories/",
            json={
                "name": "Без авторизации"
            },
        )

        assert response.status_code in  [401, 403]

    async def test_category_name_uniqueness(self, async_client: AsyncClient):
        """Проверка уникальности названий категорий"""
        # Создаем категорию напрямую в БД
        await Category.create(name="Уникальная")

        response = await async_client.get("/api/categories/")
        data = response.json()

        # Проверяем, что в списке только одна категория с таким именем
        unique_names = [cat["name"] for cat in data]
        assert unique_names.count("Уникальная") == 1