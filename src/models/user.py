"""
User model for authentication
"""
from datetime import datetime
from pydantic import BaseModel, Field


class User(BaseModel):
    """User model"""
    id: str
    username: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserCreate(BaseModel):
    """User creation model"""
    username: str
    password: str


class UserLogin(BaseModel):
    """User login model"""
    username: str
    password: str


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data"""
    username: str | None = None
