from pydantic import BaseModel, Field


class CacheMetricsResponse(BaseModel):
    service: str
    redis_available: bool
    hits: int = Field(ge=0)
    misses: int = Field(ge=0)
    writes: int = Field(ge=0)
    errors: int = Field(ge=0)
    hit_rate_percent: float = Field(ge=0, le=100)
    card_keys: int = Field(ge=0)
    used_memory_human: str | None = None
    connected_clients: int | None = None
    uptime_in_seconds: int | None = None
