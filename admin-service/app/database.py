from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


def _make_sync_url(url: str) -> str:
    return (
        url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
        .replace("postgresql+psycopg2://", "postgresql+psycopg://")
    )


auth_engine = create_engine(_make_sync_url(settings.auth_database_url))
user_engine = create_engine(_make_sync_url(settings.user_database_url))
lobby_engine = create_engine(_make_sync_url(settings.lobby_database_url))

AuthSessionLocal = sessionmaker(bind=auth_engine, autoflush=False, autocommit=False)
UserSessionLocal = sessionmaker(bind=user_engine, autoflush=False, autocommit=False)
LobbySessionLocal = sessionmaker(bind=lobby_engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_auth_db():
    db = AuthSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_db():
    db = UserSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_lobby_db():
    db = LobbySessionLocal()
    try:
        yield db
    finally:
        db.close()
