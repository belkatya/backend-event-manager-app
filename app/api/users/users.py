# app/api/users/users.py
from fastapi import APIRouter, Depends
from typing import Sequence
from db.models import User, Event
from api.schemas import (
    BaseUser,
    UserUpdate,
    PasswordChange,
    BaseEvent
)
from api.dependencies import get_current_user
from api.exceptions import BadRequestException
from config import verify_password, get_password_hash
from fastapi_pagination import Page, paginate
from fastapi_pagination.ext.tortoise import paginate as tortoise_paginate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=BaseUser)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=BaseUser)
async def update_current_user_profile(
        user_data: UserUpdate,
        current_user: User = Depends(get_current_user)
):
    update_data = user_data.model_dump(exclude_unset=True, exclude_none=True)

    if not update_data:
        return current_user

    # Update user fields
    for field, value in update_data.items():
        setattr(current_user, field, value)

    await current_user.save()

    # Refresh to get updated timestamps
    await current_user.refresh_from_db()
    return current_user


@router.patch("/me/password", response_model=dict)
async def change_password(
        password_data: PasswordChange,
        current_user: User = Depends(get_current_user)
):
    # Verify old password
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise BadRequestException("Incorrect old password")

    # Check if new password is same as old
    if verify_password(password_data.new_password, current_user.hashed_password):
        raise BadRequestException("New password must be different from old password")

    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    await current_user.save()

    return {"message": "Password changed successfully"}
