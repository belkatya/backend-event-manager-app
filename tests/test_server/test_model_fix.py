import pytest
import pytest_asyncio
from tortoise import Tortoise
from app.db.models import Location, User, Event, Category


@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_db():
    """Простая инициализация базы данных."""
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

    yield

    await Tortoise.close_connections()


@pytest.mark.asyncio
async def test_model_relationships():
    """Тест связей между моделями."""
    # Создаем тестовые записи
    user = await User.create(
        email="test@example.com",
        first_name="Тест",
        last_name="Пользователь",
        hashed_password="hashed_password"
    )

    location = await Location.create(
        city="Москва",
        street="Тверская",
        house="1"
    )

    category = await Category.create(name="Концерт")

    # Создаем событие со связями
    event = await Event.create(
        title="Тестовое событие",
        short_description="Короткое описание",
        full_description="Полное описание",
        date="2024-12-31",
        time="19:00:00",
        location=location,
        organizer=user,
        likes_count=0,
        participants_count=0
    )

    # Добавляем категорию
    await event.categories.add(category)

    # Проверяем связи
    event_from_db = await Event.get(id=event.id).prefetch_related("location", "organizer", "categories")

    assert event_from_db.location.city == "Москва"
    assert event_from_db.organizer.email == "test@example.com"
    assert len(event_from_db.categories) == 1
    assert event_from_db.categories[0].name == "Концерт"

    print("✓ Тест связей моделей прошел успешно")