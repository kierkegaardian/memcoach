from pydantic import BaseModel

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
    mastery_status: str = "new"

    class Config:
        from_attributes = True
