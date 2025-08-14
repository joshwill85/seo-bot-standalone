"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr
from typing import Dict, Any

from ...middleware.auth import jwt_auth, api_key_auth, get_current_user
from ...middleware.rate_limiting import rate_limit

router = APIRouter()
security = HTTPBearer()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/login", response_model=TokenResponse)
@rate_limit(requests=5, window=60)  # 5 login attempts per minute
async def login(request: Request, login_data: LoginRequest):
    """Authenticate user and return access tokens."""
    # In production, this would validate against database
    if login_data.email == "admin@example.com" and login_data.password == "password":
        user_data = {
            "user_id": "user_123",
            "email": login_data.email,
            "role": "admin"
        }
        
        access_token = jwt_auth.create_access_token(user_data)
        refresh_token = jwt_auth.create_refresh_token(user_data)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=24 * 3600  # 24 hours
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )


@router.post("/register", response_model=TokenResponse)
@rate_limit(requests=3, window=300)  # 3 registrations per 5 minutes
async def register(request: Request, register_data: RegisterRequest):
    """Register new user account."""
    # In production, this would create user in database
    user_data = {
        "user_id": f"user_{hash(register_data.email)}",
        "email": register_data.email,
        "role": "user"
    }
    
    access_token = jwt_auth.create_access_token(user_data)
    refresh_token = jwt_auth.create_refresh_token(user_data)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=24 * 3600
    )


@router.post("/refresh", response_model=TokenResponse)
@rate_limit(requests=10, window=60)
async def refresh_token(request: Request, refresh_data: RefreshRequest):
    """Refresh access token using refresh token."""
    access_token = jwt_auth.refresh_access_token(refresh_data.refresh_token)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_data.refresh_token,  # Keep same refresh token
        expires_in=24 * 3600
    )


@router.get("/me")
async def get_current_user_info(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user information."""
    return {
        "user_id": user.get("user_id"),
        "email": user.get("email"),
        "role": user.get("role"),
        "auth_type": user.get("auth_type"),
        "permissions": user.get("permissions", [])
    }


@router.post("/api-keys")
async def create_api_key(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    """Create new API key for authenticated user."""
    api_key = api_key_auth.create_api_key(user["user_id"])
    
    return {
        "api_key": api_key,
        "type": "live",
        "created_at": "2024-01-01T00:00:00Z",
        "permissions": ["read", "write"]
    }


@router.post("/logout")
async def logout(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    """Logout user (invalidate token)."""
    # In production, you'd add token to blacklist
    return {"message": "Successfully logged out"}