from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.shop import router as shop_router
from app.api.users import router as users_router
from app.core.config import settings
from app.db.init_db import init_db
from app.services.llm import ensure_model_available


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await init_db()
    await ensure_model_available()
    yield


app = FastAPI(title=settings.service_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(users_router)
app.include_router(shop_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}
