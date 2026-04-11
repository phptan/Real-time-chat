"""
Auth Service — Pydantic Schemas
Định nghĩa request/response cho các endpoint xác thực.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Any
from uuid import UUID


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    username: str
    password: str


class VerifyTokenRequest(BaseModel):
    token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str


class UserInfo(BaseModel):
    id: str
    username: str
    email: str
    is_online: bool = False


class StandardResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: str
