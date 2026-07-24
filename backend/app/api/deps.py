from typing import Generator
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_token
from app.models.user import User

# Standard OAuth2 scheme supporting header auth
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)

def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: str | None = Depends(oauth2_scheme)
) -> User:
    # Try resolving token from Authorization header first, then fallback to HttpOnly cookie
    actual_token = token
    if not actual_token:
        actual_token = request.cookies.get("access_token")
        if actual_token and actual_token.startswith("Bearer "):
            actual_token = actual_token[7:]
    
    if not actual_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_email = verify_token(actual_token)
    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
        
    return user
