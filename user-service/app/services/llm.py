import json
import logging
import random
import re

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

THEMES = [
    "fire",
    "ocean",
    "space",
    "forest",
    "crystal",
    "shadow",
    "gold",
    "neon",
    "ice",
    "thunder",
    "desert",
    "volcano",
    "aurora",
    "cosmos",
    "mythical",
]

RARITY_LEVELS = {
    "common": {"label": "Обычная", "price": 10, "quality": "простое"},
    "rare": {"label": "Редкая", "price": 25, "quality": "интересное"},
    "epic": {"label": "Эпическая", "price": 50, "quality": "эпическое"},
    "legendary": {"label": "Легендарная", "price": 100, "quality": "легендарное"},
    "woman": {"label": "ЖЕНЩИНА", "price": 1, "quality": "особое"},
}

PROMPT_TEMPLATE = """Сгенерируй коллекционную карточку для игры Бинго.
Тема: {theme}. Редкость: {rarity}.
Придумай {quality} название и описание.

Верни ТОЛЬКО JSON без markdown:
{{"name": "название карточки", "description": "описание карточки 1-2 предложения", "emoji": "один эмодзи", "colors": ["цвет1", "цвет2"], "image_prompt": "detailed English prompt for Stable Diffusion image generation, card game art style, dark fantasy"}}"""


def parse_json_response(text: str) -> dict | None:
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```", "", text)
    text = text.strip()

    match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def fallback_card(theme: str, rarity: str) -> dict:
    rarity_info = RARITY_LEVELS.get(rarity, RARITY_LEVELS["common"])
    if rarity == "woman":
        return {
            "name": "ЖЕНЩИНА",
            "description": "Эксклюзивная коллекционная карточка.",
            "emoji": "👩",
            "colors": ["#ff5dbd", "#8a4dff"],
            "image_prompt": "naked woman in cyberpunk style, 512x512",
        }
    return {
        "name": f"{theme.title()} Card",
        "description": f"Коллекционная карточка темы {theme}, редкость: {rarity_info['label']}.",
        "emoji": "🎴",
        "colors": ["#8a4dff", "#00bfa5"],
        "image_prompt": f"A mystical {theme} themed card game art, dark fantasy style, dramatic lighting, card game illustration, 512x512",
    }


async def ensure_model_available() -> None:
    if not settings.ollama_url or not settings.ollama_model:
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{settings.ollama_url}/api/tags")
            if response.is_success:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                if any(settings.ollama_model in name for name in model_names):
                    logger.info("Модель %s уже доступна", settings.ollama_model)
                    return

            logger.info("Скачиваем модель %s...", settings.ollama_model)
            async with httpx.AsyncClient(timeout=300.0) as pull_client:
                await pull_client.post(
                    f"{settings.ollama_url}/api/pull",
                    json={"name": settings.ollama_model, "stream": False},
                )
            logger.info("Модель %s скачана", settings.ollama_model)
    except httpx.HTTPError as exc:
        logger.warning("Не удалось проверить/скачать модель Ollama: %s", exc)


async def generate_card(theme: str, rarity: str) -> dict:
    if not settings.ollama_url or not settings.ollama_model:
        return fallback_card(theme, rarity)

    rarity_info = RARITY_LEVELS.get(rarity, RARITY_LEVELS["common"])
    prompt = PROMPT_TEMPLATE.format(
        theme=theme,
        rarity=rarity_info["label"],
        quality=rarity_info["quality"],
    )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.ollama_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            response.raise_for_status()
            result = response.json()
            raw_text = result.get("response", "")

            card_data = parse_json_response(raw_text)
            if card_data and "name" in card_data and "description" in card_data:
                card_data.setdefault("emoji", "🎴")
                card_data.setdefault("colors", ["#8a4dff", "#00bfa5"])
                card_data.setdefault(
                    "image_prompt",
                    f"A mystical {theme} themed card game art, dark fantasy style, dramatic lighting, card game illustration, 512x512",
                )
                return card_data

            logger.warning("LLM вернул невалидный JSON, используем fallback")
            return fallback_card(theme, rarity)

    except httpx.HTTPError as exc:
        logger.warning("Ошибка вызова Ollama: %s", exc)
        return fallback_card(theme, rarity)


def get_random_theme() -> str:
    return random.choice(THEMES)


def get_catalog() -> list[dict]:
    return [
        {
            "rarity": rarity,
            "label": info["label"],
            "price": info["price"],
        }
        for rarity, info in RARITY_LEVELS.items()
    ]


def get_price_by_rarity(rarity: str) -> int | None:
    info = RARITY_LEVELS.get(rarity)
    return info["price"] if info else None
