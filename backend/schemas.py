# schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str
    plan: str # Add plan to the token response

class TokenData(BaseModel):
    email: Optional[EmailStr] = None

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    plan: str
    
    class Config:
        from_attributes = True # Changed from orm_mode for Pydantic v2

# --- Stripe Schemas ---
class CheckoutSessionRequest(BaseModel):
    priceId: str