from typing import Any

from app.core.config import settings
from app.schemas.cache_metrics import CacheMetricsResponse
from app.schemas.cards import CardResponse, PlayerProgressResponse
from app.services.cache_metrics import get_cache_metrics, increment_cache_metric
from app.services.cards import card_pattern_progress, generate_card, mark_number


CARD_TTL_SECONDS = 60 * 60 * 24


class CardRepository:
    def __init__(self, redis_client: Any):
        self.redis_client = redis_client

    def key(self, game_id: str, user_id: str) -> str:
        return f"{settings.redis_key_prefix}:cards:{game_id}:{user_id}"

    def card_key(self, card_id: str) -> str:
        return f"{settings.redis_key_prefix}:card-history:{card_id}"

    def history_key(self, game_id: str, user_id: str) -> str:
        return f"{settings.redis_key_prefix}:card-history-index:{game_id}:{user_id}"

    async def get(self, game_id: str, user_id: str) -> CardResponse | None:
        try:
            raw_card = await self.redis_client.get(self.key(game_id, user_id))
        except Exception:
            await increment_cache_metric(self.redis_client, "errors")
            raise

        if raw_card is None:
            await increment_cache_metric(self.redis_client, "misses")
            return None

        await increment_cache_metric(self.redis_client, "hits")
        return CardResponse.model_validate_json(raw_card)

    async def get_by_id(self, card_id: str) -> CardResponse | None:
        try:
            raw_card = await self.redis_client.get(self.card_key(card_id))
        except Exception:
            await increment_cache_metric(self.redis_client, "errors")
            raise

        if raw_card is None:
            await increment_cache_metric(self.redis_client, "misses")
            return None

        await increment_cache_metric(self.redis_client, "hits")
        return CardResponse.model_validate_json(raw_card)

    async def get_history(self, game_id: str, user_id: str) -> list[CardResponse]:
        card_ids = await self.redis_client.smembers(self.history_key(game_id, user_id))
        cards: list[CardResponse] = []

        for card_id in card_ids:
            card = await self.get_by_id(card_id)
            if card is not None:
                cards.append(card)

        return sorted(cards, key=lambda card: card.created_at)

    async def get_room_progress(
        self,
        game_id: str,
        user_ids: list[str],
        winning_pattern: str,
    ) -> list[PlayerProgressResponse]:
        progress_items: list[PlayerProgressResponse] = []

        for user_id in dict.fromkeys(str(user_id) for user_id in user_ids):
            card = await self.get(game_id=game_id, user_id=user_id)
            if card is None:
                progress_items.append(
                    PlayerProgressResponse(
                        user_id=user_id,
                        progress=0,
                        total=0,
                        has_card=False,
                        is_complete=False,
                    )
                )
                continue

            progress, total = card_pattern_progress(card, winning_pattern)
            progress_items.append(
                PlayerProgressResponse(
                    user_id=user_id,
                    progress=progress,
                    total=total,
                    has_card=True,
                    is_complete=progress == total,
                )
            )

        return progress_items

    async def save(self, card: CardResponse) -> CardResponse:
        payload = card.model_dump_json()

        try:
            await self.redis_client.set(
                self.key(card.game_id, card.user_id),
                payload,
                ex=CARD_TTL_SECONDS,
            )
            await self.redis_client.set(
                self.card_key(card.card_id),
                payload,
                ex=CARD_TTL_SECONDS,
            )
            await self.redis_client.sadd(self.history_key(card.game_id, card.user_id), card.card_id)
            await self.redis_client.expire(self.history_key(card.game_id, card.user_id), CARD_TTL_SECONDS)
        except Exception:
            await increment_cache_metric(self.redis_client, "errors")
            raise

        await increment_cache_metric(self.redis_client, "writes")
        return card

    async def metrics(self) -> CacheMetricsResponse:
        return await get_cache_metrics(self.redis_client)

    async def create(self, game_id: str, user_id: str) -> CardResponse:
        existing_card = await self.get(game_id, user_id)
        if existing_card is not None:
            return existing_card

        card = generate_card(game_id=game_id, user_id=user_id)
        return await self.save(card)

    async def mark(
        self,
        game_id: str,
        user_id: str,
        number: int,
    ) -> tuple[CardResponse | None, bool]:
        card = await self.get(game_id=game_id, user_id=user_id)
        if card is None:
            return None, False

        card, matched = mark_number(card=card, number=number)
        await self.save(card)
        return card, matched
