from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CollectedCard(Base):
    __tablename__ = "collected_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    auth_user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    card_name: Mapped[str] = mapped_column(String(120), nullable=False)
    card_description: Mapped[str] = mapped_column(Text, nullable=False)
    card_theme: Mapped[str] = mapped_column(String(50), nullable=False)
    card_rarity: Mapped[str] = mapped_column(String(20), nullable=False)
    card_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    purchased_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
