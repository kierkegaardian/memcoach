from pydantic import BaseModel
from typing import Optional

class DeckBase(BaseModel):
    name: str

class DeckCreate(DeckBase):
    pass

class Deck(DeckBase):
    id: int

    class Config:
        from_attributes = True
