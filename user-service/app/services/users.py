from decimal import Decimal

from fastapi import HTTPException, status
import httpx
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserCreateFromAuthEvent, UserUpdateRequest


async def get_user_by_id(session: AsyncSession, user_id: int) -> User:
    user = await session.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль пользователя не найден.",
        )

    return user


async def get_user_by_auth_user_id(session: AsyncSession, auth_user_id: int) -> User:
    user = await session.scalar(select(User).where(User.auth_user_id == auth_user_id))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль пользователя не найден.",
        )

    return user


async def create_user_from_auth_event(
    session: AsyncSession,
    payload: UserCreateFromAuthEvent,
) -> User:
    existing_user = await session.scalar(
        select(User).where(
            or_(
                User.auth_user_id == payload.auth_user_id,
                User.username == payload.username,
                User.email == payload.email,
            ),
        ),
    )

    if existing_user:
        return existing_user

    user = User(
        auth_user_id=payload.auth_user_id,
        username=payload.username,
        email=str(payload.email),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def sync_auth_user_identity(
    auth_user_id: int,
    payload: UserUpdateRequest,
) -> None:
    body = payload.model_dump(exclude_none=True)

    if not body:
        return

    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
            response = await client.patch(
                f"{settings.auth_service_url}/auth/internal/users/{auth_user_id}",
                json=body,
                headers={"X-Internal-Service-Token": settings.internal_service_token},
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Не удалось синхронизировать профиль с auth-service.",
        ) from exc

    if response.status_code == status.HTTP_409_CONFLICT:
        detail = response.json().get("detail", "Email или username уже занят.")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    if not response.is_success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth-service не обновил данные профиля.",
        )


async def update_user_profile(
    session: AsyncSession,
    auth_user_id: int,
    payload: UserUpdateRequest,
) -> User:
    user = await get_user_by_auth_user_id(session, auth_user_id)

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
                detail="Профиль с таким email или username уже существует.",
            )

    await sync_auth_user_identity(auth_user_id, payload)

    if payload.username is not None:
        user.username = payload.username

    if payload.email is not None:
        user.email = str(payload.email)

    await session.commit()
    await session.refresh(user)
    return user


async def increase_user_balance(
    session: AsyncSession,
    auth_user_id: int,
    amount: Decimal,
) -> User:
    user = await get_user_by_auth_user_id(session, auth_user_id)
    user.balance += amount

    await session.commit()
    await session.refresh(user)
    return user
