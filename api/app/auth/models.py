from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: str
    full_name: str
    role: str # 'admin' or 'viewer'

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
