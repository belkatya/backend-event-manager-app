# tests/test_server/test_events.py
import pytest
from httpx import AsyncClient
from db.models import User, Event, Category, Location
from datetime import datetime, timedelta, date
import json


@pytest.mark.asyncio
class TestEventsAPI:
    """Тесты для API событий"""

    async def _create_test_user(self, async_client: AsyncClient, email: str) -> tuple:
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
        data = response.json()
        return data["access_token"], data["id"]

    async def _create_test_category(self) -> Category:
        """Создание тестовой категории"""
        category = await Category.create(name="Тестовая категория")
        return category

    async def _create_test_location(self) -> Location:
        """Создание тестовой локации"""
        location = await Location.create(
            city="Москва",
            street="Тестовая улица",
            house="10"
        )
        return location

    # ==================== ОСНОВНЫЕ ТЕСТЫ СОБЫТИЙ ====================

    async def test_create_event_success(self, async_client: AsyncClient):
        """Успешное создание события"""
        token, user_id = await self._create_test_user(async_client, "event_creator@example.com")
        category = await self._create_test_category()
        location = await self._create_test_location()

        future_date = (datetime.now() + timedelta(days=7)).date()
        future_time = (datetime.now() + timedelta(hours=1)).time()

        response = await async_client.post(
            "/api/events/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Тестовое событие",
                "short_description": "Короткое описание",
                "full_description": "Полное описание события",
                "date": future_date.isoformat(),
                "time": future_time.isoformat(),
                "location_id": location.id,
                "category_ids": [category.id],
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Проверяем обязательные поля
        assert data["title"] == "Тестовое событие"
        assert data["short_description"] == "Короткое описание"
        assert data["full_description"] == "Полное описание события"
        assert data["date"] == future_date.isoformat()
        assert "time" in data
        assert data["location"]["id"] == location.id
        assert data["location"]["city"] == "Москва"
        assert len(data["categories"]) == 1
        assert data["categories"][0]["id"] == category.id
        assert data["organizer"]["id"] == user_id
        assert data["likes_count"] == 0
        assert data["participants_count"] == 0
        assert "created_at" in data
        assert "updated_at" in data

    async def test_get_all_events_unauthorized(self, async_client: AsyncClient):
        """Получение списка событий без авторизации"""
        response = await async_client.get("/api/events/")
        assert response.status_code == 200  # Теперь работает без авторизации
        data = response.json()
        assert isinstance(data, dict)  # Пагинированный ответ

    async def test_get_all_events_with_status_requires_auth(self, async_client: AsyncClient):
        """Получение событий со статусами требует авторизации"""
        response = await async_client.get("/api/events/with-status")
        assert response.status_code in [401, 403]  # Требует авторизации

    async def test_get_events_with_status_success(self, async_client: AsyncClient):
        """Успешное получение событий со статусами пользователя"""
        token, user_id = await self._create_test_user(async_client, "status_viewer@example.com")

        # Создаем тестовые данные
        category = await self._create_test_category()
        location = await self._create_test_location()

        # Создаем пользователя для организации
        organizer = await User.create(
            email="organizer@example.com",
            first_name="Организатор",
            last_name="Событий",
            hashed_password="hashed"
        )

        # Создаем события
        event1 = await Event.create(
            title="Событие 1",
            short_description="Описание 1",
            full_description="Полное описание 1",
            date=date.today() + timedelta(days=7),
            time=datetime.now().time(),
            location=location,
            organizer=organizer,
            likes_count=5,
            participants_count=10
        )
        await event1.categories.add(category)

        # Лайкаем одно событие
        user = await User.get(id=user_id)
        await user.liked_events.add(event1)

        response = await async_client.get(
            "/api/events/with-status",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Проверяем структуру ответа
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data

        # Проверяем статусы
        if len(data["items"]) > 0:
            event = data["items"][0]
            assert "is_liked" in event
            assert "is_registered" in event
            assert event["is_liked"] is True or event["is_liked"] is False
            assert event["is_registered"] is True or event["is_registered"] is False

    async def test_get_event_with_status(self, async_client: AsyncClient):
        """Получение конкретного события со статусом пользователя"""
        token, user_id = await self._create_test_user(async_client, "event_status@example.com")

        category = await self._create_test_category()
        location = await self._create_test_location()
        user = await User.get(id=user_id)

        event = await Event.create(
            title="Событие со статусом",
            short_description="Описание",
            full_description="Полное описание",
            date=date.today() + timedelta(days=7),
            time=datetime.now().time(),
            location=location,
            organizer=user,
        )
        await event.categories.add(category)

        # Лайкаем событие
        await user.liked_events.add(event)

        response = await async_client.get(
            f"/api/events/{event.id}/with-status",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == event.id
        assert data["is_liked"] is True
        assert data["is_registered"] is False  # Не зарегистрированы

    async def test_get_event_with_status_not_found(self, async_client: AsyncClient):
        """Получение несуществующего события со статусом"""
        token, _ = await self._create_test_user(async_client, "notfound_status@example.com")

        response = await async_client.get(
            "/api/events/999999/with-status",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    # ==================== ТЕСТЫ СТАТУСОВ (лайки/регистрация) ====================

    async def test_toggle_like(self, async_client: AsyncClient):
        """Переключение лайка"""
        token, user_id = await self._create_test_user(async_client, "toggle_liker@example.com")
        category = await self._create_test_category()
        location = await self._create_test_location()
        user = await User.get(id=user_id)

        event = await Event.create(
            title="Событие для лайка",
            short_description="Описание",
            full_description="Полное описание",
            date=date.today() + timedelta(days=7),
            time=datetime.now().time(),
            location=location,
            organizer=user,
        )
        await event.categories.add(category)

        # Первый раз - ставим лайк
        response1 = await async_client.post(
            f"/api/events/{event.id}/like",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["likes_count"] == 1

        # Проверяем статус
        status_response = await async_client.get(
            f"/api/events/{event.id}/with-status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert status_response.json()["is_liked"] is True

        # Второй раз - убираем лайк
        response2 = await async_client.post(
            f"/api/events/{event.id}/like",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["likes_count"] == 0

        # Проверяем статус
        status_response2 = await async_client.get(
            f"/api/events/{event.id}/with-status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert status_response2.json()["is_liked"] is False

    async def test_register_and_unregister(self, async_client: AsyncClient):
        """Регистрация и отмена регистрации"""
        token, user_id = await self._create_test_user(async_client, "register_user@example.com")
        category = await self._create_test_category()
        location = await self._create_test_location()
        user = await User.get(id=user_id)

        event = await Event.create(
            title="Событие для регистрации",
            short_description="Описание",
            full_description="Полное описание",
            date=date.today() + timedelta(days=7),
            time=datetime.now().time(),
            location=location,
            organizer=user,
        )
        await event.categories.add(category)

        # Регистрируемся
        response1 = await async_client.post(
            f"/api/events/{event.id}/register",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["participants_count"] == 1

        # Проверяем статус
        status_response = await async_client.get(
            f"/api/events/{event.id}/with-status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert status_response.json()["is_registered"] is True

        # Пытаемся зарегистрироваться повторно
        response2 = await async_client.post(
            f"/api/events/{event.id}/register",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response2.status_code == 400  # Already registered

        # Отменяем регистрацию
        response3 = await async_client.delete(
            f"/api/events/{event.id}/register",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response3.status_code == 200

        # Проверяем статус
        status_response2 = await async_client.get(
            f"/api/events/{event.id}/with-status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert status_response2.json()["is_registered"] is False

    # ==================== ТЕСТЫ ПОЛЬЗОВАТЕЛЬСКИХ КОЛЛЕКЦИЙ ====================

    async def test_get_my_created_events_with_status(self, async_client: AsyncClient):
        """Получение созданных событий со статусами"""
        token, user_id = await self._create_test_user(async_client, "created_status@example.com")
        category = await self._create_test_category()
        location = await self._create_test_location()
        user = await User.get(id=user_id)

        # Создаем событие
        event = await Event.create(
            title="Мое событие",
            short_description="Описание",
            full_description="Полное описание",
            date=date.today() + timedelta(days=7),
            time=datetime.now().time(),
            location=location,
            organizer=user,
        )
        await event.categories.add(category)

        # Лайкаем свое событие
        await user.liked_events.add(event)

        response = await async_client.get(
            "/api/events/me/created/with-status",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert len(data["items"]) >= 1

        event_data = data["items"][0]
        assert event_data["title"] == "Мое событие"
        assert event_data["is_liked"] is True
        assert "is_registered" in event_data

    async def test_get_my_liked_events_with_status(self, async_client: AsyncClient):
        """Получение лайкнутых событий со статусами"""
        token, user_id = await self._create_test_user(async_client, "liked_status@example.com")
        category = await self._create_test_category()
        location = await self._create_test_location()
        user = await User.get(id=user_id)

        # Создаем другого организатора
        organizer = await User.create(
            email="other_org@example.com",
            first_name="Другой",
            last_name="Организатор",
            hashed_password="hashed"
        )

        # Создаем событие
        event = await Event.create(
            title="Чужое событие",
            short_description="Описание",
            full_description="Полное описание",
            date=date.today() + timedelta(days=7),
            time=datetime.now().time(),
            location=location,
            organizer=organizer,
        )
        await event.categories.add(category)

        # Лайкаем событие
        await user.liked_events.add(event)

        response = await async_client.get(
            "/api/events/me/liked/with-status",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert len(data["items"]) >= 1

        event_data = data["items"][0]
        assert event_data["is_liked"] is True  # Всегда true для лайкнутых
        assert event_data["is_registered"] is False  # Не зарегистрированы

    async def test_get_my_registered_events_with_status(self, async_client: AsyncClient):
        """Получение зарегистрированных событий со статусами"""
        token, user_id = await self._create_test_user(async_client, "registered_status@example.com")
        category = await self._create_test_category()
        location = await self._create_test_location()
        user = await User.get(id=user_id)

        # Создаем другого организатора
        organizer = await User.create(
            email="event_org@example.com",
            first_name="Организатор",
            last_name="События",
            hashed_password="hashed"
        )

        # Создаем событие
        event = await Event.create(
            title="Событие для регистрации",
            short_description="Описание",
            full_description="Полное описание",
            date=date.today() + timedelta(days=7),
            time=datetime.now().time(),
            location=location,
            organizer=organizer,
        )
        await event.categories.add(category)

        # Регистрируемся на событие
        await user.registered_events.add(event)

        response = await async_client.get(
            "/api/events/me/registered/with-status",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert len(data["items"]) >= 1

        event_data = data["items"][0]
        assert event_data["is_registered"] is True  # Всегда true для зарегистрированных
        assert "is_liked" in event_data

    # ==================== ТЕСТЫ СТАТИСТИКИ ====================

    async def test_get_my_event_stats(self, async_client: AsyncClient):
        """Получение статистики пользователя"""
        token, user_id = await self._create_test_user(async_client, "stats_user@example.com")
        category = await self._create_test_category()
        location = await self._create_test_location()
        user = await User.get(id=user_id)

        # Создаем другого пользователя для организации
        other_user = await User.create(
            email="other_stats@example.com",
            first_name="Другой",
            last_name="Пользователь",
            hashed_password="hashed"
        )

        # Создаем несколько событий
        event1 = await Event.create(
            title="Мое событие 1",
            short_description="Описание",
            full_description="Полное описание",
            date=date.today() + timedelta(days=7),
            time=datetime.now().time(),
            location=location,
            organizer=user,
        )
        await event1.categories.add(category)

        event2 = await Event.create(
            title="Мое событие 2",
            short_description="Описание",
            full_description="Полное описание",
            date=date.today() + timedelta(days=14),
            time=datetime.now().time(),
            location=location,
            organizer=user,
        )
        await event2.categories.add(category)

        event3 = await Event.create(
            title="Чужое событие",
            short_description="Описание",
            full_description="Полное описание",
            date=date.today() + timedelta(days=21),
            time=datetime.now().time(),
            location=location,
            organizer=other_user,
        )
        await event3.categories.add(category)

        # Лайкаем события
        await user.liked_events.add(event1)
        await user.liked_events.add(event3)

        # Регистрируемся на события
        await user.registered_events.add(event1)
        await user.registered_events.add(event2)

        response = await async_client.get(
            "/api/events/stats/my",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "created_events" in data
        assert "liked_events" in data
        assert "registered_events" in data

        assert data["created_events"] == 2
        assert data["liked_events"] == 2
        assert data["registered_events"] == 2

    # ==================== ФИЛЬТРАЦИЯ И СОРТИРОВКА ====================

    async def test_filter_events_future_only(self, async_client: AsyncClient):
        """Фильтрация показывает только будущие события"""
        token, user_id = await self._create_test_user(async_client, "future_filter@example.com")
        category = await self._create_test_category()
        location = await self._create_test_location()
        user = await User.get(id=user_id)

        # Создаем события: одно в прошлом, одно сегодня, одно в будущем
        past_event = await Event.create(
            title="Прошедшее событие",
            short_description="Описание",
            full_description="Полное описание",
            date=date.today() - timedelta(days=7),
            time=datetime.now().time(),
            location=location,
            organizer=user,
        )
        await past_event.categories.add(category)

        future_event = await Event.create(
            title="Будущее событие",
            short_description="Описание",
            full_description="Полное описание",
            date=date.today() + timedelta(days=7),
            time=datetime.now().time(),
            location=location,
            organizer=user,
        )
        await future_event.categories.add(category)

        response = await async_client.get(
            "/api/events/",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        if isinstance(data, dict) and 'items' in data:
            events = data['items']
        else:
            events = data

        # Должны быть только будущие события
        for event in events:
            event_date = datetime.fromisoformat(event["date"].replace('Z', '+00:00')).date()
            assert event_date >= date.today()

    # ==================== ИСПРАВЛЕНИЯ СТАРЫХ ТЕСТОВ ====================

    async def test_get_all_events_empty(self, async_client: AsyncClient):
        """Получение списка событий (пустой)"""
        # Не требует авторизации
        response = await async_client.get("/api/events/")

        assert response.status_code == 200
        data = response.json()

        # Проверяем структуру пагинации
        assert isinstance(data, dict)
        assert 'items' in data
        assert 'total' in data
        assert 'page' in data
        assert 'size' in data
        assert 'pages' in data

        events = data['items']
        assert isinstance(events, list)
        assert len(events) == 0

    async def test_get_event_by_id_success(self, async_client: AsyncClient):
        """Получение события по ID"""
        # Создаем тестовые данные
        user = await User.create(
            email="single_event@example.com",
            first_name="Организатор",
            last_name="События",
            hashed_password="hashed_password"
        )

        category = await Category.create(name="Технологии")
        location = await Location.create(city="Казань", street="Кремлевская", house="5")

        event = await Event.create(
            title="IT-конференция",
            short_description="Конференция по технологиям",
            full_description="Годовая IT-конференция с ведущими спикерами",
            date=date.today() + timedelta(days=21),
            time=datetime.now().time(),
            location=location,
            organizer=user,
            likes_count=15,
            participants_count=100
        )
        await event.categories.add(category)

        # Получаем событие по ID (не требует авторизации)
        response = await async_client.get(f"/api/events/{event.id}")

        assert response.status_code == 200
        data = response.json()

        # Проверяем детали события
        assert data["id"] == event.id
        assert data["title"] == "IT-конференция"
        assert data["short_description"] == "Конференция по технологиям"
        assert data["full_description"] == "Годовая IT-конференция с ведущими спикерами"
        assert data["location"]["city"] == "Казань"
        assert data["location"]["street"] == "Кремлевская"
        assert data["location"]["house"] == "5"
        assert len(data["categories"]) == 1
        assert data["categories"][0]["name"] == "Технологии"
        assert data["organizer"]["id"] == user.id
        assert data["organizer"]["email"] == "single_event@example.com"
        assert data["likes_count"] == 15
        assert data["participants_count"] == 100

    # Дополним тест на фильтрацию, чтобы он использовал правильный endpoint
    async def test_filter_events_by_category(self, async_client: AsyncClient):
        """Фильтрация событий по категории"""
        # Создаем тестовые данные
        user = await User.create(
            email="filter_user@example.com",
            first_name="Тест",
            last_name="Пользователь",
            hashed_password="hashed_password"
        )

        category_music = await Category.create(name="Музыка")
        category_sport = await Category.create(name="Спорт")

        location = await Location.create(city="Москва", street="Улица", house="1")

        # Создаем события
        event1 = await Event.create(
            title="Концерт",
            short_description="Музыкальный концерт",
            full_description="Концерт",
            date=date.today() + timedelta(days=7),
            time=datetime.now().time(),
            location=location,
            organizer=user,
            likes_count=5,
            participants_count=20
        )
        await event1.categories.add(category_music)

        event2 = await Event.create(
            title="Марафон",
            short_description="Спортивный марафон",
            full_description="Марафон",
            date=date.today() + timedelta(days=14),
            time=datetime.now().time(),
            location=location,
            organizer=user,
            likes_count=3,
            participants_count=15
        )
        await event2.categories.add(category_sport)

        # Фильтруем по категории "Музыка" (без авторизации)
        response = await async_client.get(f"/api/events/?category_id={category_music.id}")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, dict)
        events = data['items']

        # Проверяем, что нашли хотя бы одно событие
        music_events = [e for e in events if any(cat["name"] == "Музыка" for cat in e["categories"])]
        assert len(music_events) >= 1

    async def test_pagination(self, async_client: AsyncClient):
        """Проверка пагинации"""
        # Создаем тестовые данные
        user = await User.create(
            email="pagination_creator@example.com",
            first_name="Тест",
            last_name="Пользователь",
            hashed_password="hashed_password"
        )

        category = await Category.create(name="Тест")
        location = await Location.create(city="Москва", street="Улица", house="1")

        # Создаем только будущие события
        for i in range(15):
            event = await Event.create(
                title=f"Событие {i}",
                short_description=f"Описание {i}",
                full_description=f"Полное описание {i}",
                date=date.today() + timedelta(days=i + 1),  # Все в будущем
                time=datetime.now().time(),
                location=location,
                organizer=user,
                likes_count=i,
                participants_count=i * 2
            )
            await event.categories.add(category)

        # Первая страница (без авторизации)
        response = await async_client.get("/api/events/?page=1&size=5")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, dict)
        assert 'items' in data
        assert len(data['items']) == 5
        assert data['page'] == 1
        assert data['size'] == 5
        assert data['total'] >= 15
        assert data['pages'] >= 3

        # Проверяем вторую страницу
        response_page2 = await async_client.get("/api/events/?page=2&size=5")
        assert response_page2.status_code == 200
        data_page2 = response_page2.json()

        assert len(data_page2['items']) == 5
        assert data_page2['page'] == 2

        # Проверяем, что события на разных страницах разные
        page1_ids = {item["id"] for item in data['items']}
        page2_ids = {item["id"] for item in data_page2['items']}
        assert page1_ids.isdisjoint(page2_ids), "Pages should have different events"