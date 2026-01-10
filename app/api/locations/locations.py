# app/api/locations/locations.py
from fastapi import APIRouter, Depends, Query
from typing import Optional

from db.models import Location, User
from api.schemas import BaseLocation, LocationCreate
from api.dependencies import get_current_user
from api.exceptions import NotFoundException
from fastapi_pagination import Page
from fastapi_pagination.ext.tortoise import paginate as tortoise_paginate

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("/", response_model=Page[BaseLocation])
async def get_locations(
        city: Optional[str] = None,
        page: int = Query(1, ge=1),
        size: int = Query(20, ge=1, le=100),
):
    """
    Получение списка локаций с возможностью фильтрации по городу.

    Параметры:
    - city: фильтр по городу (регистронезависимый поиск по подстроке)
    - page: номер страницы (начиная с 1)
    - size: количество элементов на странице (1-100)
    """
    query = Location.all()

    if city:
        query = query.filter(city__icontains=city)

    query = query.order_by("city", "street", "house")
    return await tortoise_paginate(query)


@router.get("/{location_id}", response_model=BaseLocation)
async def get_location(location_id: int):
    """
    Получение локации по ID.

    Параметры:
    - location_id: ID локации
    """
    location = await Location.get_or_none(id=location_id)
    if not location:
        raise NotFoundException("Location not found")
    return location


@router.post("/", response_model=BaseLocation)
async def create_location(
        location_data: LocationCreate,
        current_user: User = Depends(get_current_user)
):
    """
    Создание новой локации.

    Требуется авторизация.

    Параметры:
    - location_data: данные для создания локации
    - current_user: текущий авторизованный пользователь
    """
    # Можно добавить проверку прав пользователя, если нужно
    # Например, только админы могут создавать локации
    # if not current_user.is_admin:
    #     raise ForbiddenException("Only administrators can create locations")

    location = await Location.create(**location_data.model_dump())
    return location