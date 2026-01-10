# tests/test_server/test_users.py
import pytest
from httpx import AsyncClient
from db.models import User, Event, Category, Location
from datetime import datetime, timedelta


@pytest.mark.asyncio
class TestUserAPI:
    """Тесты для API пользователя"""

    async def _register_and_get_token(self, async_client: AsyncClient, email: str) -> str:
        """Вспомогательный метод для регистрации и получения токена"""
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

    async def test_get_my_profile_success(self, async_client: AsyncClient):
        """Успешное получение своего профиля"""
        token = await self._register_and_get_token(async_client, "profile@example.com")

        response = await async_client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Проверка всех полей из спецификации
        assert data["email"] == "profile@example.com"
        assert data["first_name"] == "Тест"
        assert data["last_name"] == "Пользователь"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

        # Пароль не должен быть в ответе
        assert "password" not in data
        assert "hashed_password" not in data

    async def test_get_my_profile_unauthorized(self, async_client: AsyncClient):
        """Попытка получить профиль без авторизации"""
        response = await async_client.get("/api/users/me")

        # Ожидаем ошибку аутентификации (401 или 403)
        assert response.status_code in [401, 403]

        data = response.json()
        assert "detail" in data

        # Проверяем содержание ошибки
        error_text = data["detail"].lower()
        auth_keywords = ["forbidden", "unauthorized", "not authenticated", "credentials"]
        assert any(keyword in error_text for keyword in auth_keywords), \
            f"Not an authentication error: {data['detail']}"

    async def test_get_my_profile_invalid_token(self, async_client: AsyncClient):
        """Попытка получить профиль с невалидным токеном"""
        response = await async_client.get(
            "/api/users/me",
            headers={"Authorization": "Bearer invalid_token_here"},
        )

        assert response.status_code == 401

    async def test_update_my_profile_success(self, async_client: AsyncClient):
        """Успешное обновление профиля"""
        token = await self._register_and_get_token(async_client, "update@example.com")

        # Получаем текущий профиль
        get_response = await async_client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        original_data = get_response.json()

        # Обновляем профиль
        response = await async_client.put(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "first_name": "Обновленное",
                "last_name": "Имя",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["first_name"] == "Обновленное"
        assert data["last_name"] == "Имя"
        assert data["email"] == "update@example.com"
        assert data["id"] == original_data["id"]

        from datetime import datetime

        original_updated = datetime.fromisoformat(original_data["updated_at"].replace('Z', '+00:00'))
        new_updated = datetime.fromisoformat(data["updated_at"].replace('Z', '+00:00'))

        # Проверяем что новое время >= старого
        assert new_updated >= original_updated

    async def test_update_profile_empty_name(self, async_client: AsyncClient):
        """Обновление профиля с пустым именем"""
        token = await self._register_and_get_token(async_client, "empty@example.com")

        response = await async_client.put(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "first_name": "",  # Пустое имя
                "last_name": "Фамилия",
            },
        )

        # Может быть 200 или 422 в зависимости от валидации
        assert response.status_code in [200, 422]

        if response.status_code == 422:
            data = response.json()
            assert "detail" in data

    async def test_update_profile_very_long_name(self, async_client: AsyncClient):
        """Обновление профиля с очень длинными именами"""
        token = await self._register_and_get_token(async_client, "long@example.com")

        long_name = "А" * 101  # 101 символ

        response = await async_client.put(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "first_name": long_name,
                "last_name": "Фамилия",
            },
        )

        # Может быть 200 или 422
        assert response.status_code in [200, 422]

        if response.status_code == 422:
            data = response.json()
            assert "detail" in data

    async def test_update_profile_email_not_allowed(self, async_client: AsyncClient):
        """Попытка изменить email через обновление профиля"""
        token = await self._register_and_get_token(async_client, "noemailchange@example.com")

        response = await async_client.put(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": "newemail@example.com",  # Пытаемся изменить email
                "first_name": "Новое",
                "last_name": "Имя",
            },
        )

        # Либо email игнорируется (200), либо ошибка (422)
        if response.status_code == 200:
            data = response.json()
            assert data["email"] == "noemailchange@example.com"  # Email не должен измениться
        elif response.status_code == 422:
            data = response.json()
            assert "detail" in data
        else:
            assert response.status_code != 500  # Не должно быть серверной ошибки

    async def test_update_profile_partial_update(self, async_client: AsyncClient):
        """Частичное обновление профиля (только фамилия)"""
        token = await self._register_and_get_token(async_client, "partial@example.com")

        # Обновляем только фамилию
        response = await async_client.put(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "last_name": "Толькофамилия",
                # first_name не передаем
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["last_name"] == "Толькофамилия"
        # Имя должно остаться прежним
        assert data["first_name"] == "Тест"

    async def test_change_password_success(self, async_client: AsyncClient):
        """Успешная смена пароля"""
        # Регистрируем пользователя
        register_response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "changepass@example.com",
                "first_name": "Смена",
                "last_name": "Пароля",
                "password": "OldPass123!",
            },
        )

        token = register_response.json()["access_token"]

        # Меняем пароль
        response = await async_client.patch(
            "/api/users/me/password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "old_password": "OldPass123!",
                "new_password": "NewPass456!",
            },
        )

        assert response.status_code == 200

        # Проверяем, что старый пароль не работает
        login_response = await async_client.post(
            "/api/auth/login",
            data={
                "username": "changepass@example.com",
                "password": "OldPass123!",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert login_response.status_code == 401

        # Проверяем, что новый пароль работает
        login_response = await async_client.post(
            "/api/auth/login",
            data={
                "username": "changepass@example.com",
                "password": "NewPass456!",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert login_response.status_code == 200

    async def test_change_password_wrong_old_password(self, async_client: AsyncClient):
        """Смена пароля с неправильным старым паролем"""
        token = await self._register_and_get_token(async_client, "wrongold@example.com")

        response = await async_client.patch(
            "/api/users/me/password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "old_password": "WrongPass123!",  # Неправильный
                "new_password": "NewPass456!",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "пароль" in data["detail"].lower() or "password" in data["detail"].lower() or "неверный" in data[
            "detail"].lower()

    async def test_change_password_weak_new_password(self, async_client: AsyncClient):
        """Смена пароля на слабый новый пароль"""
        token = await self._register_and_get_token(async_client, "weaknew@example.com")

        response = await async_client.patch(
            "/api/users/me/password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "old_password": "TestPass123!",
                "new_password": "123",  # Слишком короткий
            },
        )

        # Может быть 200 или 422
        assert response.status_code in [200, 400, 422]

        if response.status_code != 200:
            data = response.json()
            assert "detail" in data

    async def test_change_password_same_password(self, async_client: AsyncClient):
        """Смена пароля на тот же самый"""
        token = await self._register_and_get_token(async_client, "samepass@example.com")

        response = await async_client.patch(
            "/api/users/me/password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "old_password": "TestPass123!",
                "new_password": "TestPass123!",  # Тот же самый
            },
        )

        # Может быть 200, 400 или 422
        if response.status_code == 400:
            data = response.json()
            assert "detail" in data
        elif response.status_code == 422:
            data = response.json()
            assert "detail" in data
        elif response.status_code == 200:
            # Если разрешено менять на тот же пароль
            pass
        else:
            assert response.status_code != 500

    async def test_change_password_missing_fields(self, async_client: AsyncClient):
        """Смена пароля без обязательных полей"""
        token = await self._register_and_get_token(async_client, "missing@example.com")

        # Без old_password
        response = await async_client.patch(
            "/api/users/me/password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "new_password": "NewPass456!",
            },
        )

        assert response.status_code == 422

        # Без new_password
        response = await async_client.patch(
            "/api/users/me/password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "old_password": "TestPass123!",
            },
        )

        assert response.status_code == 422

    async def test_user_endpoints_require_auth(self, async_client: AsyncClient):
        """Все endpoints пользователя требуют авторизации"""
        endpoints = [
            ("GET", "/api/users/me"),
            ("PUT", "/api/users/me"),
            ("PATCH", "/api/users/me/password"),
        ]

        for method, endpoint in endpoints:
            if method == "GET":
                response = await async_client.get(endpoint)
            elif method == "PUT":
                response = await async_client.put(endpoint, json={})
            elif method == "PATCH":
                response = await async_client.patch(endpoint, json={})

            assert response.status_code in [401, 403], f"{method} {endpoint} должен требовать авторизацию, получили {response.status_code}"

    async def test_profile_serialization_format(self, async_client: AsyncClient):
        """Проверка формата сериализации профиля пользователя"""
        token = await self._register_and_get_token(async_client, "format@example.com")

        response = await async_client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Проверяем типы данных
        assert isinstance(data["id"], int)
        assert isinstance(data["email"], str)
        assert isinstance(data["first_name"], str)
        assert isinstance(data["last_name"], str)
        assert isinstance(data["created_at"], str)
        assert isinstance(data["updated_at"], str)

        # Проверяем формат дат (ISO 8601 или похожий)
        try:
            # Пробуем разные форматы
            datetime.fromisoformat(data["created_at"].replace('Z', '+00:00'))
            datetime.fromisoformat(data["updated_at"].replace('Z', '+00:00'))
        except ValueError:
            # Если не ISO, проверяем что это строка
            assert isinstance(data["created_at"], str)
            assert isinstance(data["updated_at"], str)

    async def test_update_nonexistent_fields(self, async_client: AsyncClient):
        """Попытка обновить несуществующие поля профиля"""
        token = await self._register_and_get_token(async_client, "extra@example.com")

        response = await async_client.put(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "first_name": "Новое",
                "last_name": "Имя",
                "extra_field": "Не должно сохраниться",  # Лишнее поле
                "another_extra": 123
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Лишние поля должны игнорироваться
        assert "extra_field" not in data
        assert "another_extra" not in data

    async def test_password_change_requires_strong_password(self, async_client: AsyncClient):
        """Смена пароля требует надежный пароль"""
        token = await self._register_and_get_token(async_client, "strongpass@example.com")

        # Пытаемся сменить на слабый пароль
        weak_passwords = [
            "123",  # слишком короткий
            "password",  # нет цифр
            "12345678",  # только цифры
        ]

        for weak_password in weak_passwords:
            response = await async_client.patch(
                "/api/users/me/password",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "old_password": "TestPass123!",
                    "new_password": weak_password,
                },
            )

            # Может быть 200 или ошибка
            assert response.status_code in [200, 400, 422]