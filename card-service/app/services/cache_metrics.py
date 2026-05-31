from typing import Any

from app.core.config import settings
from app.schemas.cache_metrics import CacheMetricsResponse


METRICS_KEY = f"{settings.redis_key_prefix}:metrics:card-cache"
CARD_KEYS_PATTERN = f"{settings.redis_key_prefix}:cards:*"
METRIC_FIELDS = ("hits", "misses", "writes", "errors")


async def increment_cache_metric(
    redis_client: Any,
    field: str,
    amount: int = 1,
) -> None:
    if field not in METRIC_FIELDS:
        return

    try:
        await redis_client.hincrby(METRICS_KEY, field, amount)
    except Exception:
        return


async def get_cache_metrics(redis_client: Any) -> CacheMetricsResponse:
    redis_available = True
    metrics = {field: 0 for field in METRIC_FIELDS}
    card_keys = 0
    info: dict[str, Any] = {}

    try:
        await redis_client.ping()
        raw_metrics = await redis_client.hgetall(METRICS_KEY)
        metrics.update(
            {
                field: int(raw_metrics.get(field, 0))
                for field in METRIC_FIELDS
            }
        )
        async for _ in redis_client.scan_iter(match=CARD_KEYS_PATTERN):
            card_keys += 1
        info = await redis_client.info()
    except Exception:
        redis_available = False

    reads = metrics["hits"] + metrics["misses"]
    hit_rate = round((metrics["hits"] / reads) * 100, 2) if reads else 0.0

    return CacheMetricsResponse(
        service=settings.service_name,
        redis_available=redis_available,
        hits=metrics["hits"],
        misses=metrics["misses"],
        writes=metrics["writes"],
        errors=metrics["errors"],
        hit_rate_percent=hit_rate,
        card_keys=card_keys,
        used_memory_human=info.get("used_memory_human"),
        connected_clients=info.get("connected_clients"),
        uptime_in_seconds=info.get("uptime_in_seconds"),
    )
