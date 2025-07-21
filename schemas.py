# schemas.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# --- User Schemas ---
class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_pro: bool
    registered_date: datetime

    class Config:
        from_attributes = True # Pydantic V2 compatibility