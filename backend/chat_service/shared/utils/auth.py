"""
Shared authentication utilities for all services.
Provides JWT token verification and user authentication.
"""

import os
import httpx
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import redis.asyncio as redis

# Configuration
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8000")
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Security
security = HTTPBearer()

# Redis connection for caching
redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client for caching."""
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            await redis_client.ping()
        except Exception:
            redis_client = None
    return redis_client


async def verify_token_with_auth_service(token: str) -> Dict[str, Any]:
    """
    Verify JWT token with the auth service.
    Returns user data if token is valid.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{AUTH_SERVICE_URL}/verify-token",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
    except httpx.RequestError:
        # If auth service is unavailable, fall back to local JWT verification
        return await verify_token_locally(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def verify_token_locally(token: str) -> Dict[str, Any]:
    """
    Verify JWT token locally as fallback when auth service is unavailable.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {"user_id": user_id, "sub": user_id}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Get current user from JWT token.
    This function can be used as a dependency in FastAPI endpoints.
    """
    token = credentials.credentials
    
    # Check Redis cache first
    redis_client = await get_redis_client()
    if redis_client:
        try:
            cached_user = await redis_client.get(f"token_user:{token}")
            if cached_user:
                import json
                return json.loads(cached_user)
        except Exception:
            pass
    
    # Verify token and get user data
    user_data = await verify_token_with_auth_service(token)
    
    # Cache user data in Redis
    if redis_client and user_data:
        try:
            await redis_client.setex(
                f"token_user:{token}",
                300,  # 5 minutes cache
                json.dumps(user_data)
            )
        except Exception:
            pass
    
    return user_data


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Get current user ID from JWT token.
    Simplified version that only returns the user ID.
    """
    user_data = await get_current_user_from_token(credentials)
    return user_data.get("user_id") or user_data.get("sub")


async def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Require admin role for the endpoint.
    Returns user data if user is admin.
    """
    user_data = await get_current_user_from_token(credentials)
    
    if user_data.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return user_data


def create_auth_middleware():
    """
    Create authentication middleware for non-FastAPI services.
    Returns a function that can verify tokens.
    """
    async def verify_token(token: str) -> Dict[str, Any]:
        """Verify JWT token and return user data."""
        return await verify_token_with_auth_service(token)
    
    return verify_token

