"""
Authentication dependencies for FastAPI
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.auth.security import decode_access_token
from src.database.users import get_user_by_username
from src.models.user import User

security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get the current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    username = decode_access_token(token)
    
    if username is None:
        raise credentials_exception
    
    user_data = get_user_by_username(username)
    if user_data is None:
        raise credentials_exception
    
    return User(
        id=user_data["id"],
        username=user_data["username"],
        created_at=user_data["created_at"]
    )
