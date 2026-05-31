from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_card_repository
from app.core.security import get_current_user_id
from app.repositories.cards import CardRepository
from app.schemas.cards import (
    CardPreviewRequest,
    CardResponse,
    MarkNumberRequest,
    MarkNumberResponse,
    PlayerProgressResponse,
    RoomProgressRequest,
    WinnerCheckData,
)
from app.services.cards import build_winner_check_data, generate_card


router = APIRouter(tags=["cards"])


@router.post("/cards/preview", response_model=CardResponse)
def preview_card(payload: CardPreviewRequest) -> CardResponse:
    return generate_card(game_id=payload.game_id, user_id=payload.user_id)


@router.post(
    "/games/{game_id}/cards/me",
    response_model=CardResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_my_card(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
    repository: CardRepository = Depends(get_card_repository),
) -> CardResponse:
    return await repository.create(game_id=game_id, user_id=user_id)


@router.get("/games/{game_id}/cards/me", response_model=CardResponse)
async def get_my_card(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
    repository: CardRepository = Depends(get_card_repository),
) -> CardResponse:
    card = await repository.get(game_id=game_id, user_id=user_id)
    if card is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found",
        )

    return card


@router.get("/games/{game_id}/cards/me/history", response_model=list[CardResponse])
async def get_my_cards_history(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
    repository: CardRepository = Depends(get_card_repository),
) -> list[CardResponse]:
    return await repository.get_history(game_id=game_id, user_id=user_id)


@router.post("/games/{game_id}/cards/progress", response_model=list[PlayerProgressResponse])
async def get_room_card_progress(
    game_id: str,
    payload: RoomProgressRequest,
    _: str = Depends(get_current_user_id),
    repository: CardRepository = Depends(get_card_repository),
) -> list[PlayerProgressResponse]:
    return await repository.get_room_progress(
        game_id=game_id,
        user_ids=payload.user_ids,
        winning_pattern=payload.winning_pattern,
    )


@router.post("/games/{game_id}/cards/me/marks", response_model=MarkNumberResponse)
async def mark_drawn_number(
    game_id: str,
    payload: MarkNumberRequest,
    user_id: str = Depends(get_current_user_id),
    repository: CardRepository = Depends(get_card_repository),
) -> MarkNumberResponse:
    card, matched = await repository.mark(
        game_id=game_id,
        user_id=user_id,
        number=payload.number,
    )
    if card is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found",
        )

    return MarkNumberResponse(matched=matched, card=card)


@router.get("/games/{game_id}/cards/me/winner-data", response_model=WinnerCheckData)
async def get_winner_check_data(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
    repository: CardRepository = Depends(get_card_repository),
) -> WinnerCheckData:
    card = await repository.get(game_id=game_id, user_id=user_id)
    if card is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found",
        )

    return build_winner_check_data(card)
