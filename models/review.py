from pydantic import BaseModel, validator
from typing import Optional
from enum import Enum

class Grade(str, Enum):
    PERFECT = "perfect"
    GOOD = "good"
    FAIL = "fail"

class ReviewCreate(BaseModel):
    card_id: int
    kid_id: int
    grade: Grade
    user_text: Optional[str] = None

    @validator('grade')
    def validate_grade(cls, v):
        if v not in Grade:
            raise ValueError("Grade must be 'perfect', 'good', or 'fail'")
        return v

class Review(ReviewCreate):
    id: int
    ts: str  # ISO datetime

    class Config:
        from_attributes = True
