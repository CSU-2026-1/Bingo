from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_current_user_id
from app.db.session import get_db_session
from app.schemas.user import BalanceUpdateRequest, UserResponse, UserUpdateRequest
from app.services.users import (
    get_user_by_auth_user_id,
    get_user_by_id,
    increase_user_balance,
    update_user_profile,
)


router = APIRouter(prefix="/users", tags=["users"])


def verify_internal_token(x_internal_service_token: str = Header(default="")) -> None:
    if not settings.internal_service_token or x_internal_service_token != settings.internal_service_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Неверный internal token.",
        )


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_auth_user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    return await get_user_by_auth_user_id(session, current_auth_user_id)


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    payload: UserUpdateRequest,
    current_auth_user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    return await update_user_profile(session, current_auth_user_id, payload)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    _: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    return await get_user_by_id(session, user_id)


@router.patch("/{auth_user_id}/balance", response_model=UserResponse)
async def update_user_balance(
    auth_user_id: int,
    payload: BalanceUpdateRequest,
    _: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    return await increase_user_balance(session, auth_user_id, payload.amount)


@router.patch("/internal/{auth_user_id}/balance", response_model=UserResponse)
async def internal_update_user_balance(
    auth_user_id: int,
    payload: BalanceUpdateRequest,
    _: None = Depends(verify_internal_token),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    return await increase_user_balance(session, auth_user_id, payload.amount)
