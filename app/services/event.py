# app/services/events.py
"""
Сервис для работы с событиями.
Содержит бизнес-логику для создания, обновления и управления событиями.
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any
from tortoise.expressions import Q
from tortoise.query_utils import Prefetch

from db.models import Event, Category, Location, User
from models.event import EventCreate, EventUpdate, EventFilterParams
from api.exceptions import NotFoundException, ForbiddenException, BadRequestException


class EventService:
    """Сервис событий"""

    async def create_event(self, event_data: EventCreate, organizer: User) -> Event:
        """
        Создает новое событие.

        Args:
            event_data: Данные события
            organizer: Организатор события

        Returns:
            Event: Созданное событие

        Raises:
            NotFoundException: Если локация или категория не найдена
            BadRequestException: Если дата события в прошлом
        """
        # Проверяем локацию
        location = await Location.get_or_none(id=event_data.location_id)
        if not location:
            raise NotFoundException("Location not found")

        # Проверяем категории
        categories = await Category.filter(id__in=event_data.category_ids).all()
        if len(categories) != len(event_data.category_ids):
            raise NotFoundException("One or more categories not found")

        # Проверяем дату (дополнительная проверка)
        if event_data.date < date.today():
            raise BadRequestException("Event date must be in the future")

        # Создаем событие
        event = await Event.create(
            title=event_data.title,
            short_description=event_data.short_description,
            full_description=event_data.full_description,
            date=event_data.date,
            time=event_data.time,
            location=location,
            organizer=organizer,
        )

        # Добавляем категории
        await event.categories.add(*categories)

        # Загружаем связанные данные для ответа
        await event.fetch_related("location", "organizer", "categories")
        return event

    async def get_event_by_id(self, event_id: int) -> Optional[Event]:
        """
        Получает событие по ID со всеми связанными данными.

        Args:
            event_id: ID события

        Returns:
            Optional[Event]: Событие или None
        """
        return await Event.filter(id=event_id).select_related(
            "location", "organizer"
        ).prefetch_related("categories").first()

    async def update_event(self, event_id: int, update_data: EventUpdate, user: User) -> Event:
        """
        Обновляет событие.

        Args:
            event_id: ID события
            update_data: Данные для обновления
            user: Пользователь, пытающийся обновить событие

        Returns:
            Event: Обновленное событие

        Raises:
            NotFoundException: Если событие, локация или категория не найдена
            ForbiddenException: Если пользователь не организатор
        """
        event = await self.get_event_by_id(event_id)
        if not event:
            raise NotFoundException("Event not found")

        # Проверяем права
        if event.organizer_id != user.id:
            raise ForbiddenException("You can only update your own events")

        # Обрабатываем обновление данных
        clean_data = update_data.model_dump(exclude_unset=True, exclude_none=True)

        # Обрабатываем обновление локации
        if "location_id" in clean_data:
            location = await Location.get_or_none(id=clean_data["location_id"])
            if not location:
                raise NotFoundException("Location not found")
            event.location = location
            del clean_data["location_id"]

        # Обрабатываем обновление категорий
        if "category_ids" in clean_data:
            categories = await Category.filter(id__in=clean_data["category_ids"]).all()
            if len(categories) != len(clean_data["category_ids"]):
                raise NotFoundException("One or more categories not found")
            await event.categories.clear()
            await event.categories.add(*categories)
            del clean_data["category_ids"]

        # Обновляем остальные поля
        for field, value in clean_data.items():
            if hasattr(event, field):
                setattr(event, field, value)

        await event.save()
        await event.fetch_related("location", "organizer", "categories")
        return event

    async def delete_event(self, event_id: int, user: User) -> None:
        """
        Удаляет событие.

        Args:
            event_id: ID события
            user: Пользователь, пытающийся удалить событие

        Raises:
            NotFoundException: Если событие не найдено
            ForbiddenException: Если пользователь не организатор
        """
        event = await Event.get_or_none(id=event_id)
        if not event:
            raise NotFoundException("Event not found")

        # Проверяем права
        if event.organizer_id != user.id:
            raise ForbiddenException("You can only delete your own events")

        await event.delete()

    async def get_events_with_filters(self, filters: EventFilterParams) -> List[Event]:
        """
        Получает события с применением фильтров.

        Args:
            filters: Параметры фильтрации

        Returns:
            List[Event]: Список событий
        """
        query = Event.all().select_related("location", "organizer").prefetch_related("categories")

        # Фильтруем по категории
        if filters.category_id:
            query = query.filter(categories__id=filters.category_id)

        # Фильтруем по городу
        if filters.city:
            query = query.filter(location__city__icontains=filters.city)

        # Поиск по ключевым словам
        if filters.search:
            search_term = filters.search.strip()
            query = query.filter(
                Q(title__icontains=search_term) |
                Q(short_description__icontains=search_term) |
                Q(full_description__icontains=search_term)
            )

        # Фильтруем только будущие события
        query = query.filter(date__gte=date.today())

        # Сортировка
        if filters.sort_by_likes == "desc":
            query = query.order_by("-likes_count", "-created_at")
        elif filters.sort_by_likes == "asc":
            query = query.order_by("likes_count", "-created_at")
        else:
            query = query.order_by("-created_at")

        return await query

    async def toggle_like(self, event_id: int, user: User) -> Event:
        """
        Переключает лайк пользователя на событии.

        Args:
            event_id: ID события
            user: Пользователь

        Returns:
            Event: Обновленное событие

        Raises:
            NotFoundException: Если событие не найдено
        """
        event = await self.get_event_by_id(event_id)
        if not event:
            raise NotFoundException("Event not found")

        # Проверяем, лайкнул ли уже пользователь
        liked = await user.liked_events.filter(id=event_id).exists()

        if liked:
            # Убираем лайк
            await user.liked_events.remove(event)
            event.likes_count = max(0, event.likes_count - 1)
        else:
            # Добавляем лайк
            await user.liked_events.add(event)
            event.likes_count += 1

        await event.save()
        await event.fetch_related("location", "organizer", "categories")
        return event

    async def register_for_event(self, event_id: int, user: User) -> Event:
        """
        Регистрирует пользователя на событие.

        Args:
            event_id: ID события
            user: Пользователь

        Returns:
            Event: Обновленное событие

        Raises:
            NotFoundException: Если событие не найдено
            BadRequestException: Если пользователь уже зарегистрирован
        """
        event = await self.get_event_by_id(event_id)
        if not event:
            raise NotFoundException("Event not found")

        # Проверяем, не зарегистрирован ли уже
        registered = await user.registered_events.filter(id=event_id).exists()
        if registered:
            raise BadRequestException("Already registered for this events")

        # Регистрируем
        await user.registered_events.add(event)
        event.participants_count += 1

        await event.save()
        await event.fetch_related("location", "organizer", "categories")
        return event

    async def unregister_from_event(self, event_id: int, user: User) -> None:
        """
        Отменяет регистрацию пользователя на событие.

        Args:
            event_id: ID события
            user: Пользователь

        Raises:
            NotFoundException: Если событие не найдено
            BadRequestException: Если пользователь не зарегистрирован
        """
        event = await self.get_event_by_id(event_id)
        if not event:
            raise NotFoundException("Event not found")

        # Проверяем, зарегистрирован ли
        registered = await user.registered_events.filter(id=event_id).exists()
        if not registered:
            raise BadRequestException("Not registered for this events")

        # Отменяем регистрацию
        await user.registered_events.remove(event)
        event.participants_count = max(0, event.participants_count - 1)

        await event.save()

    async def get_user_created_events(self, user: User) -> List[Event]:
        """
        Получает события, созданные пользователем.

        Args:
            user: Пользователь

        Returns:
            List[Event]: Список созданных событий
        """
        return await Event.filter(organizer=user).select_related(
            "location", "organizer"
        ).prefetch_related("categories").order_by("-created_at").all()

    async def get_user_liked_events(self, user: User) -> List[Event]:
        """
        Получает события, которые понравились пользователю.

        Args:
            user: Пользователь

        Returns:
            List[Event]: Список лайкнутых событий
        """
        return await Event.filter(liked_by__id=user.id).select_related(
            "location", "organizer"
        ).prefetch_related("categories").order_by("-created_at").all()

    async def get_user_registered_events(self, user: User) -> List[Event]:
        """
        Получает события, на которые пользователь зарегистрирован.

        Args:
            user: Пользователь

        Returns:
            List[Event]: Список зарегистрированных событий
        """
        return await Event.filter(participants__id=user.id).select_related(
            "location", "organizer"
        ).prefetch_related("categories").order_by("-created_at").all()


# Экземпляр сервиса для использования
event_service = EventService()