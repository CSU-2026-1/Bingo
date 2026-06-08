from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class CatalogItem(BaseModel):
    rarity: str
    label: str
    price: int


class PurchaseRequest(BaseModel):
    rarity: str


class CollectedCardResponse(BaseModel):
    id: int
    card_name: str
    card_description: str
    card_theme: str
    card_rarity: str
    card_metadata: dict | None
    image_url: str | None = None
    purchased_at: datetime

    model_config = {"from_attributes": True}


class PurchaseResponse(BaseModel):
    card: CollectedCardResponse
    new_balance: Decimal
