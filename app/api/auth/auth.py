#app/api/auth/auth.py
# app/api/auth/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional
from datetime import datetime, timedelta

from db.models import User
from api.schemas import UserRegister, TokenResponse, MessageResponse
from api.dependencies import get_current_user
from api.exceptions import AuthException, BadRequestException
from config import (
    verify_password,
    get_password_hash,
    create_user_access_token,
    create_access_token
)
from config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    # Check if user already exists
    existing_user = await User.get_or_none(email=user_data.email)
    if existing_user:
        raise BadRequestException("User with this email already exists")

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    user = await User.create(
        email=user_data.email,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        hashed_password=hashed_password,
    )

    # Create access token
    access_token = create_user_access_token(user)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await User.get_or_none(email=form_data.username)

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise AuthException("Incorrect email or password")

    # Create access token
    access_token = create_user_access_token(user)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(current_user: User = Depends(get_current_user)):
    # In JWT implementation, logout is handled client-side
    # We could implement token blacklist here if needed
    return MessageResponse(message="Successfully logged out")