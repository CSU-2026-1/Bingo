from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    InternalUserUpdateRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
)
from app.services.events import publish_user_registered


async def register_user(
    session: AsyncSession,
    payload: UserRegisterRequest,
) -> AuthResponse:
    existing_user = await session.scalar(
        select(User).where(
            or_(
                User.email == payload.email,
                User.username == payload.username,
            ),
        ),
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email или username уже существует.",
        )

    user = User(
        username=payload.username,
        email=str(payload.email),
        hashed_password=hash_password(payload.password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    await publish_user_registered(user)

    return AuthResponse(
        user=user,
        token=TokenResponse(access_token=create_access_token(user.id, user.username)),
    )


async def login_user(
    session: AsyncSession,
    payload: UserLoginRequest,
) -> AuthResponse:
    user = await session.scalar(select(User).where(User.email == payload.email))

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль.",
        )

    return AuthResponse(
        user=user,
        token=TokenResponse(access_token=create_access_token(user.id, user.username)),
    )


async def get_current_user(session: AsyncSession, user_id: int) -> User:
    user = await session.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден.",
        )

    return user


async def update_user_identity(
    session: AsyncSession,
    user_id: int,
    payload: InternalUserUpdateRequest,
) -> User:
    user = await get_current_user(session, user_id)

    if payload.username is not None or payload.email is not None:
        duplicate_user = await session.scalar(
            select(User).where(
                User.id != user.id,
                or_(
                    User.username == payload.username,
                    User.email == payload.email,
                ),
            ),
        )

        if duplicate_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Пользователь с таким email или username уже существует.",
            )

    if payload.username is not None:
        user.username = payload.username

    if payload.email is not None:
        user.email = str(payload.email)

    await session.commit()
    await session.refresh(user)
    return user
