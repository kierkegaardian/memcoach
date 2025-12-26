from pydantic import BaseModel
from typing import Optional
from datetime import date
from decimal import Decimal

class CardBase(BaseModel):
    deck_id: int
    prompt: str
    full_text: str

class CardCreate(CardBase):
    pass

class Card(CardBase):
    id: int
    interval_days: int = 1
    due_date: str  # ISO date
    ease_factor: float = 2.5
    streak: int = 0

    class Config:
        from_attributes = True
