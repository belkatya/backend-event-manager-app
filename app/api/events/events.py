# app/api/events/events.py
from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from datetime import date, datetime

from db.models import Event, Category, Location, User
from api.schemas import (
    BaseEvent,
    EventCreate,
    EventUpdate,
    EventFilterParams,
    MessageResponse,
    EventWithUserStatus,
    PaginatedEventsWithStatus
)
from api.dependencies import get_current_user, get_current_user_optional
from api.exceptions import (
    NotFoundException,
    ForbiddenException,
    BadRequestException,
    ValidationException
)
from fastapi_pagination import Page, add_pagination, paginate
from fastapi_pagination.ext.tortoise import paginate as tortoise_paginate
from tortoise.expressions import Q
from tortoise.functions import Count

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/", response_model=Page[BaseEvent])
async def get_events(
        category_id: Optional[int] = None,
        city: Optional[str] = None,
        search: Optional[str] = None,
        sort_by_likes: Optional[str] = None,
        page: int = Query(1, ge=1),
        size: int = Query(20, ge=1, le=100),
        current_user: Optional[User] = Depends(get_current_user_optional)
):
    query = Event.all().select_related("location", "organizer").prefetch_related("categories")

    # Apply filters
    if category_id:
        query = query.filter(categories__id=category_id)

    if city:
        query = query.filter(location__city__icontains=city)

    if search:
        query = query.filter(
            Q(title__icontains=search) |
            Q(short_description__icontains=search) |
            Q(full_description__icontains=search)
        )

    # Apply sorting
    if sort_by_likes == "desc":
        query = query.order_by("-likes_count", "-created_at")
    elif sort_by_likes == "asc":
        query = query.order_by("likes_count", "-created_at")
    else:
        query = query.order_by("-created_at")

    # Filter out past events (only future events)
    query = query.filter(date__gte=date.today())

    # Если пользователь авторизован, можем добавить статусы
    # Но FastAPI Pagination не поддерживает кастомные модели с дополнительными полями
    # Для этого нужен отдельный эндпоинт или кастомная пагинация
    return await tortoise_paginate(query)


@router.get("/with-status", response_model=PaginatedEventsWithStatus)
async def get_events_with_status(
        category_id: Optional[int] = None,
        city: Optional[str] = None,
        search: Optional[str] = None,
        sort_by_likes: Optional[str] = None,
        page: int = Query(1, ge=1),
        size: int = Query(20, ge=1, le=100),
        current_user: User = Depends(get_current_user)  # Требуем авторизацию
):
    """Получить события со статусами пользователя (лайк/регистрация)"""
    query = Event.all().select_related("location", "organizer").prefetch_related("categories")

    # Apply filters
    if category_id:
        query = query.filter(categories__id=category_id)

    if city:
        query = query.filter(location__city__icontains=city)

    if search:
        query = query.filter(
            Q(title__icontains=search) |
            Q(short_description__icontains=search) |
            Q(full_description__icontains=search)
        )

    # Apply sorting
    if sort_by_likes == "desc":
        query = query.order_by("-likes_count", "-created_at")
    elif sort_by_likes == "asc":
        query = query.order_by("likes_count", "-created_at")
    else:
        query = query.order_by("-created_at")

    # Filter out past events (only future events)
    query = query.filter(date__gte=date.today())

    # Получаем общее количество
    total = await query.count()

    # Вычисляем offset и limit для пагинации
    offset = (page - 1) * size
    events = await query.offset(offset).limit(size).all()

    # Добавляем статусы пользователя
    events_with_status = []
    for event in events:
        # Проверяем лайк
        is_liked = await current_user.liked_events.filter(id=event.id).exists()
        # Проверяем регистрацию
        is_registered = await current_user.registered_events.filter(id=event.id).exists()

        # Создаем BaseEvent из модели
        base_event = BaseEvent.model_validate(event)
        # Создаем EventWithUserStatus с добавленными статусами
        event_with_status = EventWithUserStatus(
            **base_event.model_dump(),
            is_liked=is_liked,
            is_registered=is_registered
        )
        events_with_status.append(event_with_status)

    return {
        "items": events_with_status,
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size  # ceil(total / size)
    }


@router.get("/{event_id}", response_model=BaseEvent)
async def get_event(
        event_id: int,
        current_user: Optional[User] = Depends(get_current_user_optional)
):
    event = await Event.get_or_none(id=event_id)
    if not event:
        raise NotFoundException("Event not found")

    await event.fetch_related("location", "organizer", "categories")
    return event


@router.get("/{event_id}/with-status", response_model=EventWithUserStatus)
async def get_event_with_status(
        event_id: int,
        current_user: User = Depends(get_current_user)  # Требуем авторизацию
):
    """Получить событие со статусом пользователя (лайк/регистрация)"""
    event = await Event.get_or_none(id=event_id)
    if not event:
        raise NotFoundException("Event not found")

    await event.fetch_related("location", "organizer", "categories")

    # Проверяем лайк
    is_liked = await current_user.liked_events.filter(id=event_id).exists()
    # Проверяем регистрацию
    is_registered = await current_user.registered_events.filter(id=event_id).exists()

    # Создаем BaseEvent из модели
    base_event = BaseEvent.model_validate(event)
    # Создаем EventWithUserStatus с добавленными статусами
    event_with_status = EventWithUserStatus(
        **base_event.model_dump(),
        is_liked=is_liked,
        is_registered=is_registered
    )

    return event_with_status


@router.post("/", response_model=BaseEvent)
async def create_event(
        event_data: EventCreate,
        current_user: User = Depends(get_current_user)
):
    # Check if location exists
    location = await Location.get_or_none(id=event_data.location_id)
    if not location:
        raise NotFoundException("Location not found")

    # Check if categories exist
    categories = await Category.filter(id__in=event_data.category_ids).all()
    if len(categories) != len(event_data.category_ids):
        raise NotFoundException("One or more categories not found")

    # Create event
    event = await Event.create(
        title=event_data.title,
        short_description=event_data.short_description,
        full_description=event_data.full_description,
        date=event_data.date,
        time=event_data.time,
        location=location,
        organizer=current_user,
    )

    # Add categories
    await event.categories.add(*categories)

    # Fetch related data for response
    await event.fetch_related("location", "organizer", "categories")
    return event


@router.put("/{event_id}", response_model=BaseEvent)
async def update_event(
        event_id: int,
        event_data: EventUpdate,
        current_user: User = Depends(get_current_user)
):
    event = await Event.get_or_none(id=event_id)
    if not event:
        raise NotFoundException("Event not found")

    # Check if user is organizer
    if event.organizer_id != current_user.id:
        raise ForbiddenException("You can only update your own events")

    update_data = event_data.model_dump(exclude_unset=True)

    # Handle location update
    if "location_id" in update_data:
        location = await Location.get_or_none(id=update_data["location_id"])
        if not location:
            raise NotFoundException("Location not found")
        event.location = location
        del update_data["location_id"]

    # Handle categories update
    if "category_ids" in update_data:
        categories = await Category.filter(id__in=update_data["category_ids"]).all()
        if len(categories) != len(update_data["category_ids"]):
            raise NotFoundException("One or more categories not found")
        await event.categories.clear()
        await event.categories.add(*categories)
        del update_data["category_ids"]

    # Update other fields
    for field, value in update_data.items():
        if value is not None:
            setattr(event, field, value)

    await event.save()
    await event.fetch_related("location", "organizer", "categories")
    return event


@router.delete("/{event_id}", response_model=MessageResponse)
async def delete_event(
        event_id: int,
        current_user: User = Depends(get_current_user)
):
    event = await Event.get_or_none(id=event_id)
    if not event:
        raise NotFoundException("Event not found")

    # Check if user is organizer
    if event.organizer_id != current_user.id:
        raise ForbiddenException("You can only delete your own events")

    await event.delete()
    return MessageResponse(message="Event deleted successfully")


@router.post("/{event_id}/like", response_model=BaseEvent)
async def toggle_like(
        event_id: int,
        current_user: User = Depends(get_current_user)
):
    event = await Event.get_or_none(id=event_id)
    if not event:
        raise NotFoundException("Event not found")

    # Check if user already liked the event
    liked = await current_user.liked_events.filter(id=event_id).exists()

    if liked:
        # Unlike
        await current_user.liked_events.remove(event)
        event.likes_count = max(0, event.likes_count - 1)
    else:
        # Like
        await current_user.liked_events.add(event)
        event.likes_count += 1

    await event.save()
    await event.fetch_related("location", "organizer", "categories")
    return event


@router.post("/{event_id}/register", response_model=BaseEvent)
async def register_for_event(
        event_id: int,
        current_user: User = Depends(get_current_user)
):
    event = await Event.get_or_none(id=event_id)
    if not event:
        raise NotFoundException("Event not found")

    # Check if already registered
    registered = await current_user.registered_events.filter(id=event_id).exists()

    if registered:
        raise BadRequestException("Already registered for this event")

    # Register
    await current_user.registered_events.add(event)
    event.participants_count += 1

    await event.save()
    await event.fetch_related("location", "organizer", "categories")
    return event


@router.delete("/{event_id}/register", response_model=MessageResponse)
async def unregister_from_event(
        event_id: int,
        current_user: User = Depends(get_current_user)
):
    event = await Event.get_or_none(id=event_id)
    if not event:
        raise NotFoundException("Event not found")

    # Check if registered
    registered = await current_user.registered_events.filter(id=event_id).exists()

    if not registered:
        raise BadRequestException("Not registered for this event")

    # Unregister
    await current_user.registered_events.remove(event)
    event.participants_count = max(0, event.participants_count - 1)

    await event.save()
    return MessageResponse(message="Successfully unregistered from event")


@router.get("/me/created", response_model=Page[BaseEvent])
async def get_my_created_events(current_user: User = Depends(get_current_user)):
    events = (
        Event.filter(organizer=current_user)
        .select_related("location", "organizer")
        .prefetch_related("categories")
        .order_by("-created_at")
    )
    return await tortoise_paginate(events)


@router.get("/me/liked", response_model=Page[BaseEvent])
async def get_my_liked_events(current_user: User = Depends(get_current_user)):
    # Используем ManyToMany связь через liked_by_users в Event
    events = (
        Event.filter(liked_by_users__id=current_user.id)
        .select_related("location", "organizer")
        .prefetch_related("categories")
        .order_by("-created_at")
    )
    return await tortoise_paginate(events)


@router.get("/me/registered", response_model=Page[BaseEvent])
async def get_my_registered_events(current_user: User = Depends(get_current_user)):
    # Используем ManyToMany связь через registered_users в Event
    events = (
        Event.filter(registered_users__id=current_user.id)
        .select_related("location", "organizer")
        .prefetch_related("categories")
        .order_by("-created_at")
    )
    return await tortoise_paginate(events)


@router.get("/me/created/with-status", response_model=PaginatedEventsWithStatus)
async def get_my_created_events_with_status(
        page: int = Query(1, ge=1),
        size: int = Query(20, ge=1, le=100),
        current_user: User = Depends(get_current_user)
):
    """Получить созданные события со статусами"""
    query = (
        Event.filter(organizer=current_user)
        .select_related("location", "organizer")
        .prefetch_related("categories")
        .order_by("-created_at")
    )

    # Получаем общее количество
    total = await query.count()

    # Вычисляем offset и limit для пагинации
    offset = (page - 1) * size
    events = await query.offset(offset).limit(size).all()

    # Добавляем статусы
    events_with_status = []
    for event in events:
        # Для созданных событий всегда лайк/регистрация от организатора
        is_liked = await current_user.liked_events.filter(id=event.id).exists()
        is_registered = await current_user.registered_events.filter(id=event.id).exists()

        # Создаем BaseEvent из модели
        base_event = BaseEvent.model_validate(event)
        # Создаем EventWithUserStatus с добавленными статусами
        event_with_status = EventWithUserStatus(
            **base_event.model_dump(),
            is_liked=is_liked,
            is_registered=is_registered
        )
        events_with_status.append(event_with_status)

    return {
        "items": events_with_status,
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size  # ceil(total / size)
    }


@router.get("/me/liked/with-status", response_model=PaginatedEventsWithStatus)
async def get_my_liked_events_with_status(
        page: int = Query(1, ge=1),
        size: int = Query(20, ge=1, le=100),
        current_user: User = Depends(get_current_user)
):
    """Получить лайкнутые события со статусами"""
    query = (
        Event.filter(liked_by__id=current_user.id)  # Исправлено: liked_by вместо liked_by_users
        .select_related("location", "organizer")
        .prefetch_related("categories")
        .order_by("-created_at")
    )

    # Получаем общее количество
    total = await query.count()

    # Вычисляем offset и limit для пагинации
    offset = (page - 1) * size
    events = await query.offset(offset).limit(size).all()

    # Добавляем статусы
    events_with_status = []
    for event in events:
        # Для лайкнутых событий всегда is_liked = True
        is_registered = await current_user.registered_events.filter(id=event.id).exists()

        # Создаем BaseEvent из модели
        base_event = BaseEvent.model_validate(event)
        # Создаем EventWithUserStatus с добавленными статусами
        event_with_status = EventWithUserStatus(
            **base_event.model_dump(),
            is_liked=True,  # Всегда true для лайкнутых
            is_registered=is_registered
        )
        events_with_status.append(event_with_status)

    return {
        "items": events_with_status,
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size  # ceil(total / size)
    }


@router.get("/me/registered/with-status", response_model=PaginatedEventsWithStatus)
async def get_my_registered_events_with_status(
        page: int = Query(1, ge=1),
        size: int = Query(20, ge=1, le=100),
        current_user: User = Depends(get_current_user)
):
    """Получить зарегистрированные события со статусами"""
    query = (
        Event.filter(participants__id=current_user.id)  # Исправлено: participants вместо registered_users
        .select_related("location", "organizer")
        .prefetch_related("categories")
        .order_by("-created_at")
    )

    # Получаем общее количество
    total = await query.count()

    # Вычисляем offset и limit для пагинации
    offset = (page - 1) * size
    events = await query.offset(offset).limit(size).all()

    # Добавляем статусы
    events_with_status = []
    for event in events:
        # Для зарегистрированных событий всегда is_registered = True
        is_liked = await current_user.liked_events.filter(id=event.id).exists()

        # Создаем BaseEvent из модели
        base_event = BaseEvent.model_validate(event)
        # Создаем EventWithUserStatus с добавленными статусами
        event_with_status = EventWithUserStatus(
            **base_event.model_dump(),
            is_liked=is_liked,
            is_registered=True  # Всегда true для зарегистрированных
        )
        events_with_status.append(event_with_status)

    return {
        "items": events_with_status,
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size  # ceil(total / size)
    }


@router.get("/stats/my", response_model=dict)
async def get_my_event_stats(current_user: User = Depends(get_current_user)):
    """Получить статистику пользователя по событиям"""
    created_count = await Event.filter(organizer=current_user).count()
    liked_count = await current_user.liked_events.all().count()
    registered_count = await current_user.registered_events.all().count()

    return {
        "created_events": created_count,
        "liked_events": liked_count,
        "registered_events": registered_count
    }


# Добавляем поддержку пагинации
add_pagination(router)