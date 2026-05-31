from fastapi import APIRouter, Depends

from app.api.dependencies import get_card_repository
from app.repositories.cards import CardRepository
from app.schemas.cache_metrics import CacheMetricsResponse


router = APIRouter(prefix="/cache", tags=["cache"])


@router.get("/metrics", response_model=CacheMetricsResponse)
async def read_cache_metrics(
    repository: CardRepository = Depends(get_card_repository),
) -> CacheMetricsResponse:
    return await repository.metrics()
