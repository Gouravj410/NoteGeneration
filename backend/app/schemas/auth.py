from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: str | None = None

class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
        # Pydantic v2 configuration style
