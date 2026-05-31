from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.core.config import settings
from app.db.session import get_db_session
from app.schemas.auth import (
    AuthResponse,
    InternalUserUpdateRequest,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth import get_current_user, login_user, register_user, update_user_identity


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
async def register(
    payload: UserRegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AuthResponse:
    return await register_user(session, payload)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: UserLoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AuthResponse:
    return await login_user(session, payload)


@router.get("/me", response_model=UserResponse)
async def me(
    current_user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    return await get_current_user(session, current_user_id)


def verify_internal_token(
    x_internal_service_token: str = Header(default=""),
) -> None:
    if x_internal_service_token != settings.internal_service_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный внутренний токен сервиса.",
        )


@router.patch("/internal/users/{user_id}", response_model=UserResponse)
async def update_internal_user(
    user_id: int,
    payload: InternalUserUpdateRequest,
    _: None = Depends(verify_internal_token),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    return await update_user_identity(session, user_id, payload)
