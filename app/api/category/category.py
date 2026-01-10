# app/api/category/category.py
from fastapi import APIRouter, Depends
from typing import List

from db.models import Category, User
from api.schemas import BaseCategory, CategoryCreate
from api.dependencies import get_current_user
from api.exceptions import BadRequestException

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=List[BaseCategory])
async def get_categories():
    categories = await Category.all().order_by("name")
    return categories


@router.post("/", response_model=BaseCategory)
async def create_category(
        category_data: CategoryCreate,
        current_user: User = Depends(get_current_user)
):
    # Check if category already exists
    existing_category = await Category.get_or_none(name=category_data.name)
    if existing_category:
        raise BadRequestException("Category with this name already exists")

    # Create category
    category = await Category.create(name=category_data.name)
    return category