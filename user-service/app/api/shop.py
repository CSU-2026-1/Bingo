from decimal import Decimal

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_current_user_id
from app.db.session import get_db_session
from app.models.collected_card import CollectedCard
from app.models.user import User
from app.schemas.shop import (
    CatalogItem,
    CollectedCardResponse,
    PurchaseRequest,
    PurchaseResponse,
)
from app.services.llm import generate_card, get_catalog, get_price_by_rarity, get_random_theme
from app.services.users import get_user_by_auth_user_id

router = APIRouter(prefix="/shop", tags=["shop"])


async def generate_image(image_prompt: str) -> str | None:
    if not settings.image_service_url:
        return None

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.image_service_url}/generate",
                json={"prompt": image_prompt},
            )
            response.raise_for_status()
            return response.json()["url"]
    except httpx.HTTPError:
        return None


@router.get("/catalog", response_model=list[CatalogItem])
async def shop_catalog() -> list[CatalogItem]:
    return [CatalogItem(**item) for item in get_catalog()]


@router.post("/purchase", response_model=PurchaseResponse)
async def purchase_card(
    payload: PurchaseRequest,
    current_auth_user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> PurchaseResponse:
    price = get_price_by_rarity(payload.rarity)
    if price is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверная редкость карточки.",
        )

    user = await get_user_by_auth_user_id(session, current_auth_user_id)

    if Decimal(str(price)) > user.balance:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Недостаточно монет для покупки.",
        )

    theme = get_random_theme()
    card_data = await generate_card(theme, payload.rarity)

    image_prompt = card_data.get("image_prompt", f"A mystical {theme} card game art, dark fantasy, 512x512")
    image_url = await generate_image(image_prompt)

    user.balance -= Decimal(str(price))

    collected_card = CollectedCard(
        auth_user_id=current_auth_user_id,
        card_name=card_data["name"],
        card_description=card_data["description"],
        card_theme=theme,
        card_rarity=payload.rarity,
        card_metadata={
            "emoji": card_data.get("emoji", "🎴"),
            "colors": card_data.get("colors", ["#8a4dff", "#00bfa5"]),
        },
        image_url=image_url,
    )
    session.add(collected_card)
    await session.commit()
    await session.refresh(collected_card)

    return PurchaseResponse(
        card=CollectedCardResponse.model_validate(collected_card),
        new_balance=user.balance,
    )


@router.get("/my-cards", response_model=list[CollectedCardResponse])
async def get_my_cards(
    current_auth_user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> list[CollectedCardResponse]:
    result = await session.execute(
        select(CollectedCard)
        .where(CollectedCard.auth_user_id == current_auth_user_id)
        .order_by(CollectedCard.purchased_at.desc())
    )
    cards = result.scalars().all()
    return [CollectedCardResponse.model_validate(c) for c in cards]


@router.get("/users/{user_id}/cards", response_model=list[CollectedCardResponse])
async def get_user_cards(
    user_id: int,
    _: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> list[CollectedCardResponse]:
    result = await session.execute(
        select(CollectedCard)
        .where(CollectedCard.auth_user_id == user_id)
        .order_by(CollectedCard.purchased_at.desc())
    )
    cards = result.scalars().all()
    return [CollectedCardResponse.model_validate(c) for c in cards]
