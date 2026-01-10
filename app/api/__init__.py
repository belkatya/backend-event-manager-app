#app/api/__init__.py
# app/api/__init__.py
from fastapi import APIRouter
from api.auth.auth import router as auth_router
from api.users.users import router as users_router
from api.events.events import router as events_router
from api.category.category import router as category_router
from api.locations.locations import router as locations_router

router = APIRouter(prefix="/api")

router.include_router(auth_router)
router.include_router(users_router)
router.include_router(events_router)
router.include_router(category_router)
router.include_router(locations_router)