#uuuuu
async def test_get_my_created_events(self, async_client: AsyncClient):
    """Получение созданных пользователем событий"""
    token = await self._register_and_get_token(async_client, "creator@example.com")

    # Получаем ID пользователя
    profile_response = await async_client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    user_id = profile_response.json()["id"]

    # Создаем категорию и локацию для теста
    category = await Category.create(name="Технологии")
    location = await Location.create(
        city="Москва",
        street="Тверская",
        house="1"
    )

    # Создаем события от имени пользователя
    event1 = await Event.create(
        title="Мое событие 1",
        short_description="Короткое описание",
        full_description="Полное описание",
        date=datetime.now().date() + timedelta(days=7),
        time=datetime.now().time(),
        location=location,
        organizer_id=user_id,
        likes_count=5,
        participants_count=10
    )
    await event1.categories.add(category)

    # Получаем созданные события через API
    response = await async_client.get(
        "/api/events/me/created",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Проверяем структуру (может быть пагинация или список)
    if isinstance(data, dict) and 'items' in data:
        events = data['items']
        # Проверяем поля пагинации
        assert 'total' in data
        assert 'page' in data
        assert 'size' in data
    else:
        events = data

    assert isinstance(events, list)
    assert len(events) >= 1

    # Проверяем, что событие принадлежит пользователю
    assert events[0]["organizer"]["id"] == user_id
    assert events[0]["title"] == "Мое событие 1"


async def test_get_my_created_events_empty(self, async_client: AsyncClient):
    """Получение созданных событий (когда их нет)"""
    token = await self._register_and_get_token(async_client, "nocreated@example.com")

    response = await async_client.get(
        "/api/events/me/created",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    if isinstance(data, dict) and 'items' in data:
        events = data['items']
    else:
        events = data

    assert isinstance(events, list)
    assert len(events) == 0


async def test_get_my_liked_events_empty(self, async_client: AsyncClient):
    """Получение лайкнутых событий (когда их нет)"""
    token = await self._register_and_get_token(async_client, "nolikes@example.com")

    response = await async_client.get(
        "/api/events/me/liked",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    if isinstance(data, dict) and 'items' in data:
        events = data['items']
    else:
        events = data

    assert isinstance(events, list)


async def test_get_my_registered_events_empty(self, async_client: AsyncClient):
    """Получение событий, на которые пользователь зарегистрирован (когда их нет)"""
    token = await self._register_and_get_token(async_client, "noreg@example.com")

    response = await async_client.get(
        "/api/events/me/registered",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()

    if isinstance(data, dict) and 'items' in data:
        events = data['items']
    else:
        events = data

    assert isinstance(events, list)