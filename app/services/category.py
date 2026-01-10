#app/services/category.py

# app/services/category.py
"""
Сервис для работы с категориями.
"""

from typing import List
from db.models import Category
from models.category import CategoryCreate
from api.exceptions import BadRequestException


class CategoryService:
    """Сервис категорий"""

    async def get_all_categories(self) -> List[Category]:
        """
        Получает все категории.

        Returns:
            List[Category]: Список всех категорий
        """
        return await Category.all().order_by("name")

    async def get_category_by_id(self, category_id: int) -> Category:
        """
        Получает категорию по ID.

        Args:
            category_id: ID категории

        Returns:
            Category: Категория

        Raises:
            NotFoundException: Если категория не найдена
        """
        category = await Category.get_or_none(id=category_id)
        if not category:
            from api.exceptions import NotFoundException
            raise NotFoundException("Category not found")
        return category

    async def create_category(self, category_data: CategoryCreate) -> Category:
        """
        Создает новую категорию.

        Args:
            category_data: Данные категории

        Returns:
            Category: Созданная категория

        Raises:
            BadRequestException: Если категория с таким именем уже существует
        """
        # Проверяем, существует ли категория с таким именем
        existing_category = await Category.get_or_none(name=category_data.name)
        if existing_category:
            raise BadRequestException("Category with this name already exists")

        # Создаем категорию
        category = await Category.create(name=category_data.name)
        return category

    async def update_category(self, category_id: int, name: str) -> Category:
        """
        Обновляет категорию.

        Args:
            category_id: ID категории
            name: Новое имя категории

        Returns:
            Category: Обновленная категория

        Raises:
            NotFoundException: Если категория не найдена
            BadRequestException: Если категория с таким именем уже существует
        """
        from api.exceptions import NotFoundException

        category = await self.get_category_by_id(category_id)

        # Проверяем, не занято ли имя другой категорией
        if name != category.name:
            existing_category = await Category.get_or_none(name=name)
            if existing_category:
                raise BadRequestException("Category with this name already exists")

        category.name = name
        await category.save()
        return category

    async def delete_category(self, category_id: int) -> None:
        """
        Удаляет категорию.

        Args:
            category_id: ID категории

        Raises:
            NotFoundException: Если категория не найдена
        """
        from api.exceptions import NotFoundException

        category = await self.get_category_by_id(category_id)
        await category.delete()


# Экземпляр сервиса для использования
category_service = CategoryService()