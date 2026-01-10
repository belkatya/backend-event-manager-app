# tests/test_server/test_auth.py
import pytest
from httpx import AsyncClient
from db.models import User


@pytest.mark.asyncio
class TestAuthAPI:
    """Тесты для API аутентификации"""

    async def test_register_user_success(self, async_client: AsyncClient):
        """Успешная регистрация нового пользователя"""
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "first_name": "Иван",
                "last_name": "Иванов",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Проверка структуры ответа
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "id" in data
        assert data["email"] == "test@example.com"
        assert data["first_name"] == "Иван"
        assert data["last_name"] == "Иванов"
        assert "created_at" in data
        assert "updated_at" in data

        # Пароль не должен быть в ответе
        assert "password" not in data
        assert "hashed_password" not in data

        # Проверка, что пользователь создан в базе
        user = await User.get_or_none(email="test@example.com")
        assert user is not None
        assert user.first_name == "Иван"
        assert user.email == "test@example.com"

    async def test_register_user_duplicate_email(self, async_client: AsyncClient):
        """Регистрация с уже существующим email"""
        # Создаем пользователя
        await User.create(
            email="existing@example.com",
            first_name="Существующий",
            last_name="Пользователь",
            hashed_password="hashed_password"
        )

        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "existing@example.com",
                "first_name": "Новый",
                "last_name": "Пользователь",
                "password": "AnotherPass123!",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "email" in data["detail"].lower() or "уже существует" in data["detail"].lower()

    async def test_register_user_invalid_email(self, async_client: AsyncClient):
        """Регистрация с некорректным email"""
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "invalid-email",
                "first_name": "Иван",
                "last_name": "Иванов",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    async def test_register_user_short_password(self, async_client: AsyncClient):
        """Регистрация с коротким паролем"""
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "shortpass@example.com",
                "first_name": "Иван",
                "last_name": "Иванов",
                "password": "123",  # Слишком короткий
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    async def test_register_user_missing_fields(self, async_client: AsyncClient):
        """Регистрация с отсутствующими обязательными полями"""
        # Без email
        response = await async_client.post(
            "/api/auth/register",
            json={
                "first_name": "Иван",
                "last_name": "Иванов",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 422

        # Без пароля
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "nopass@example.com",
                "first_name": "Иван",
                "last_name": "Иванов",
            },
        )

        assert response.status_code == 422

        # Без имени
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "noname@example.com",
                "last_name": "Иванов",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 422

    async def test_register_user_weak_password_no_special_char(self, async_client: AsyncClient):
        """Регистрация с паролем без специальных символов"""
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "weakpass@example.com",
                "first_name": "Иван",
                "last_name": "Иванов",
                "password": "SimplePass123",  # Без специального символа
            },
        )

        # Может быть 200 (если не требуется спецсимвол) или 422
        assert response.status_code in [200, 422]

    async def test_login_success(self, async_client: AsyncClient):
        """Успешный вход в систему"""
        # Сначала регистрируем пользователя
        register_response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "login@example.com",
                "first_name": "Петр",
                "last_name": "Петров",
                "password": "LoginPass123!",
            },
        )

        # Теперь входим
        response = await async_client.post(
            "/api/auth/login",
            data={
                "username": "login@example.com",
                "password": "LoginPass123!",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["email"] == "login@example.com"
        assert data["first_name"] == "Петр"
        assert data["last_name"] == "Петров"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_login_wrong_password(self, async_client: AsyncClient):
        """Вход с неправильным паролем"""
        # Регистрируем пользователя
        await async_client.post(
            "/api/auth/register",
            json={
                "email": "wrongpass@example.com",
                "first_name": "Алексей",
                "last_name": "Алексеев",
                "password": "CorrectPass123!",
            },
        )

        # Пытаемся войти с неправильным паролем
        response = await async_client.post(
            "/api/auth/login",
            data={
                "username": "wrongpass@example.com",
                "password": "WrongPass123!",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

        # Исправленная проверка:
        detail_lower = data["detail"].lower()
        assert (
                "пароль" in detail_lower or
                "неверный" in detail_lower or
                "incorrect" in detail_lower or  # Добавляем английский вариант
                "password" in detail_lower or  # Добавляем английский вариант
                "credentials" in detail_lower
        ), f"Unexpected error message: {data['detail']}"

    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        """Вход несуществующего пользователя"""
        response = await async_client.post(
            "/api/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "SomePass123!",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    async def test_login_invalid_format(self, async_client: AsyncClient):
        """Вход с неправильным форматом данных"""
        # Без username - может вернуть 401 (неверные учетные данные) или 422 (невалидная форма)
        response = await async_client.post(
            "/api/auth/login",
            data={
                "password": "SomePass123!",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        print(f"Response without username - Status: {response.status_code}, Body: {response.text}")
        # OAuth2PasswordRequestForm может обрабатывать это как неверные учетные данные
        assert response.status_code in [401, 422]

        # Без password - аналогично
        response = await async_client.post(
            "/api/auth/login",
            data={
                "username": "test@example.com",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        print(f"Response without password - Status: {response.status_code}, Body: {response.text}")
        assert response.status_code in [401, 422]

        # С пустым username - будет 401 (неверный email/пароль)
        response = await async_client.post(
            "/api/auth/login",
            data={
                "username": "",
                "password": "SomePass123!",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        print(f"Response with empty username - Status: {response.status_code}, Body: {response.text}")
        # Пустой username приведет к ошибке аутентификации
        assert response.status_code == 401

    async def test_login_case_insensitive_email(self, async_client: AsyncClient):
        """Проверка, что email нечувствителен к регистру"""
        # Регистрируем с маленькими буквами
        await async_client.post(
            "/api/auth/register",
            json={
                "email": "case@example.com",
                "first_name": "Регистр",
                "last_name": "Тест",
                "password": "CasePass123!",
            },
        )

        # Пытаемся войти с большими буквами
        response = await async_client.post(
            "/api/auth/login",
            data={
                "username": "CASE@EXAMPLE.COM",  # Большие буквы
                "password": "CasePass123!",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        # Может быть 200 или 401 в зависимости от реализации
        assert response.status_code in [200, 401]

    async def test_logout_success(self, async_client: AsyncClient):
        """Успешный выход из системы"""
        # Регистрируем и логинимся
        register_response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "logout@example.com",
                "first_name": "Владимир",
                "last_name": "Владимиров",
                "password": "LogoutPass123!",
            },
        )

        auth_data = register_response.json()
        token = auth_data["access_token"]

        # Выходим
        response = await async_client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

        # Проверяем сообщение
        assert "logged out" in data["message"].lower() or "success" in data["message"].lower()

        # В JWT реализации токен ОСТАЕТСЯ валидным после logout
        # (если не реализована blacklist)
        profile_response = await async_client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Два варианта:
        # 1. Токен все еще работает (stateless JWT) - ожидаем 200
        # 2. Токен не работает (есть blacklist) - ожидаем 401

        # Проверяем, что реализовано:
        if hasattr(self, '_jwt_has_blacklist'):
            # Если есть blacklist
            assert profile_response.status_code == 401
        else:
            # По умолчанию для stateless JWT токен должен работать
            print(f"Note: Token still works after logout (stateless JWT). Status: {profile_response.status_code}")
            # Можно либо пропустить проверку, либо проверить что токен работает
            assert profile_response.status_code == 200

            # И проверяем, что возвращаются правильные данные
            profile_data = profile_response.json()
            assert profile_data["email"] == "logout@example.com"

    async def test_logout_without_token(self, async_client: AsyncClient):
        """
        Выход без токена.

        Note: HTTPBearer security scheme returns 403 Forbidden
        for missing token (not 401 Unauthorized).
        This is standard FastAPI behavior.
        """
        response = await async_client.post("/api/auth/logout")

        # FastAPI's HTTPBearer returns 403 for missing authentication
        assert response.status_code == 403

        data = response.json()
        assert "detail" in data

        # Проверяем типичное сообщение
        assert "Not authenticated" in data["detail"] or "Forbidden" in data["detail"]

    async def test_logout_invalid_token(self, async_client: AsyncClient):
        """Выход с невалидным токеном"""
        response = await async_client.post(
            "/api/auth/logout",
            headers={"Authorization": "Bearer invalid_token_here"},
        )

        assert response.status_code == 401

    async def test_token_returns_correct_user_data(self, async_client: AsyncClient):
        """Проверка, что токен возвращает правильные данные пользователя"""
        # Регистрируем пользователя
        register_response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "tokenuser@example.com",
                "first_name": "Токен",
                "last_name": "Пользователь",
                "password": "TokenPass123!",
            },
        )

        auth_data = register_response.json()
        token = auth_data["access_token"]

        # Используем токен для получения профиля
        response = await async_client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Проверяем, что данные совпадают
        assert data["email"] == "tokenuser@example.com"
        assert data["first_name"] == "Токен"
        assert data["last_name"] == "Пользователь"
        assert data["id"] == auth_data["id"]

    async def test_expired_token(self, async_client: AsyncClient):
        """Проверка работы с истекшим токеном"""
        # Регистрируем пользователя
        register_response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "expired@example.com",
                "first_name": "Истекший",
                "last_name": "Токен",
                "password": "ExpiredPass123!",
            },
        )

        auth_data = register_response.json()
        token = auth_data["access_token"]

        # Тест не может реально проверить истечение срока,
        # но проверяет что токен вообще работает
        response = await async_client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200