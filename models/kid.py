from pydantic import BaseModel
from typing import Optional

class KidBase(BaseModel):
    name: str

class KidCreate(KidBase):
    pass

class Kid(KidBase):
    id: int

    class Config:
        from_attributes = True
