# app/services/location.py
"""
Сервис для работы с локациями.
"""

from typing import List, Optional
from tortoise.expressions import Q

from db.models import Location
from models.location import LocationCreate, LocationUpdate
from api.exceptions import NotFoundException, BadRequestException


class LocationService:
    """Сервис локаций"""

    async def get_all_locations(self, city: Optional[str] = None) -> List[Location]:
        """
        Получает все локации с возможностью фильтрации по городу.

        Args:
            city: Фильтр по городу

        Returns:
            List[Location]: Список локаций
        """
        query = Location.all()

        if city:
            query = query.filter(city__icontains=city)

        return await query.order_by("city", "street", "house").all()

    async def get_locations_paginated(
            self,
            city: Optional[str] = None,
            page: int = 1,
            size: int = 20
    ) -> tuple[List[Location], int]:
        """
        Получает локации с пагинацией.

        Args:
            city: Фильтр по городу
            page: Номер страницы
            size: Размер страницы

        Returns:
            tuple: (список локаций, общее количество)
        """
        query = Location.all()

        if city:
            query = query.filter(city__icontains=city)

        # Получаем общее количество
        total = await query.count()

        # Применяем пагинацию
        offset = (page - 1) * size
        locations = await query.offset(offset).limit(size).order_by("city", "street", "house").all()

        return locations, total

    async def get_location_by_id(self, location_id: int) -> Location:
        """
        Получает локацию по ID.

        Args:
            location_id: ID локации

        Returns:
            Location: Локация

        Raises:
            NotFoundException: Если локация не найдена
        """
        location = await Location.get_or_none(id=location_id)
        if not location:
            raise NotFoundException("Location not found")
        return location

    async def create_location(self, location_data: LocationCreate) -> Location:
        """
        Создает новую локацию.

        Args:
            location_data: Данные локации

        Returns:
            Location: Созданная локация

        Raises:
            BadRequestException: Если локация уже существует
        """
        # Проверяем, не существует ли уже такая локация
        existing_location = await Location.get_or_none(
            city=location_data.city,
            street=location_data.street,
            house=location_data.house
        )

        if existing_location:
            raise BadRequestException("Location already exists")

        # Создаем локацию
        location = await Location.create(**location_data.model_dump())
        return location

    async def update_location(self, location_id: int, update_data: LocationUpdate) -> Location:
        """
        Обновляет локацию.

        Args:
            location_id: ID локации
            update_data: Данные для обновления

        Returns:
            Location: Обновленная локация

        Raises:
            NotFoundException: Если локация не найдена
            BadRequestException: Если локация с такими данными уже существует
        """
        location = await self.get_location_by_id(location_id)

        # Получаем только установленные поля
        clean_data = update_data.model_dump(exclude_unset=True, exclude_none=True)

        if not clean_data:
            return location

        # Проверяем, не дублируется ли новая локация
        if 'city' in clean_data or 'street' in clean_data or 'house' in clean_data:
            city = clean_data.get('city', location.city)
            street = clean_data.get('street', location.street)
            house = clean_data.get('house', location.house)

            existing_location = await Location.get_or_none(
                city=city,
                street=street,
                house=house
            )

            if existing_location and existing_location.id != location_id:
                raise BadRequestException("Location with these details already exists")

        # Обновляем поля
        for field, value in clean_data.items():
            if hasattr(location, field):
                setattr(location, field, value)

        await location.save()
        return location

    async def delete_location(self, location_id: int) -> None:
        """
        Удаляет локацию.

        Args:
            location_id: ID локации

        Raises:
            NotFoundException: Если локация не найдена
        """
        location = await self.get_location_by_id(location_id)
        await location.delete()

    async def search_locations(self, search_query: str) -> List[Location]:
        """
        Ищет локации по всем текстовым полям.

        Args:
            search_query: Поисковый запрос

        Returns:
            List[Location]: Найденные локации
        """
        if not search_query:
            return await self.get_all_locations()

        query = search_query.strip()

        locations = await Location.filter(
            Q(city__icontains=query) |
            Q(street__icontains=query) |
            Q(house__icontains=query)
        ).order_by("city", "street", "house").all()

        return locations

    async def get_cities(self) -> List[str]:
        """
        Получает список всех уникальных городов.

        Returns:
            List[str]: Список городов
        """
        locations = await Location.all().distinct().order_by("city").values_list("city", flat=True)
        return list(locations)

    async def get_locations_by_city(self, city: str) -> List[Location]:
        """
        Получает все локации в конкретном городе.

        Args:
            city: Город

        Returns:
            List[Location]: Локации в городе
        """
        return await Location.filter(city__iexact=city).order_by("street", "house").all()

    async def validate_location_exists(self, location_id: int) -> bool:
        """
        Проверяет, существует ли локация.

        Args:
            location_id: ID локации

        Returns:
            bool: True если локация существует
        """
        return await Location.filter(id=location_id).exists()

    async def get_or_create_location(self, location_data: LocationCreate) -> tuple[Location, bool]:
        """
        Получает или создает локацию.

        Args:
            location_data: Данные локации

        Returns:
            tuple: (локация, created) где created=True если была создана новая локация
        """
        existing_location = await Location.get_or_none(
            city=location_data.city,
            street=location_data.street,
            house=location_data.house
        )

        if existing_location:
            return existing_location, False

        new_location = await self.create_location(location_data)
        return new_location, True

    async def get_location_stats(self) -> dict:
        """
        Получает статистику по локациям.

        Returns:
            dict: Статистика
        """
        total_locations = await Location.all().count()
        cities = await self.get_cities()
        locations_per_city = {}

        for city in cities:
            count = await Location.filter(city=city).count()
            locations_per_city[city] = count

        return {
            "total_locations": total_locations,
            "total_cities": len(cities),
            "cities": cities,
            "locations_per_city": locations_per_city
        }


# Экземпляр сервиса для использования
location_service = LocationService()