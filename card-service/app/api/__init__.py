from fastapi import APIRouter

from app.api.routes.cache import router as cache_router
from app.api.routes.cards import router as cards_router


router = APIRouter()
router.include_router(cards_router)
router.include_router(cache_router)
