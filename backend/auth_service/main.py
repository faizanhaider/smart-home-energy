"""
FastAPI Authentication Service for Smart Home Energy Monitoring.
"""

import os
import time
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
import redis.asyncio as redis
import httpx

from shared.database.connection import get_db, create_tables
from shared.models import User

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Initialize FastAPI app
app = FastAPI(
    title="Smart Home Energy - Auth Service",
    description="Authentication and user management service",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT") == "development" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") == "development" else None
)

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Redis connection
redis_client: Optional[redis.Redis] = None

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global redis_client
    
    # Create database tables
    create_tables()
    
    # Initialize Redis connection
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        print("✅ Redis connected successfully")
    except Exception as e:
        print(f"⚠️  Redis connection failed: {e}")
        redis_client = None


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    if redis_client:
        await redis_client.close()


# Utility functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    
    # Convert UUID objects to strings for JSON serialization
    for key, value in to_encode.items():
        if hasattr(value, 'hex'):  # Check if it's a UUID
            to_encode[key] = str(value)
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Check Redis cache first
    if redis_client:
        try:
            # Convert user_id to string for Redis key
            user_id_str = str(user_id) if hasattr(user_id, 'hex') else user_id
            cached_user = await redis_client.get(f"user:{user_id_str}")
            if cached_user:
                import json
                user_data = json.loads(cached_user)
                # Convert string ID back to UUID if needed
                if 'id' in user_data and isinstance(user_data['id'], str):
                    try:
                        from uuid import UUID
                        user_data['id'] = UUID(user_data['id'])
                    except ValueError:
                        pass  # If UUID conversion fails, continue with string
                return User(**user_data)
        except Exception:
            pass
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    # Cache user in Redis
    if redis_client:
        try:
            # Use the safer JSON serialization method
            user_json = user.to_json()
            # Convert user_id to string for Redis key
            user_id_str = str(user_id) if hasattr(user_id, 'hex') else user_id
            await redis_client.setex(
                f"user:{user_id_str}", 
                300,  # 5 minutes cache
                user_json
            )
        except Exception:
            pass
    
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Pydantic models
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID


class UserCreate(BaseModel):
    """User registration model."""
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserLogin(BaseModel):
    """User login model."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response model."""
    id: UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str
    expires_in: int


# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "auth-service",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


@app.post("/login", response_model=Token)
async def login_user(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token."""
    try:
        # Find user by email
        user = db.query(User).filter(User.email == user_credentials.email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not verify_password(user_credentials.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.id}, expires_delta=access_token_expires
        )
        
        # Store token in Redis for potential blacklisting
        if redis_client:
            try:
                # Convert UUID to string for Redis storage
                user_id_str = str(user.id) if hasattr(user.id, 'hex') else user.id
                await redis_client.setex(
                    f"token:{access_token}",
                    ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                    user_id_str
                )
            except Exception:
                pass
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )


@app.post("/logout")
async def logout_user(current_user: User = Depends(get_current_user)):
    """Logout user by blacklisting their token."""
    # This would require storing the token in the request context
    # For now, we'll just return success
    return {"message": "Successfully logged out"}


@app.get("/profile", response_model=UserResponse)
async def get_user_profile(current_user: User = Depends(get_current_active_user)):
    """Get current user profile."""
    return current_user


@app.put("/profile", response_model=UserResponse)
async def update_user_profile(
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user profile."""
    update_data = {}
    if first_name is not None:
        update_data["first_name"] = first_name
    if last_name is not None:
        update_data["last_name"] = last_name
    
    if update_data:
        current_user.update(db, **update_data)
    
    # Clear Redis cache
    if redis_client:
        try:
            user_id_str = str(current_user.id) if hasattr(current_user.id, 'hex') else current_user.id
            await redis_client.delete(f"user:{user_id_str}")
        except Exception:
            pass
    
    return current_user


@app.get("/users", response_model=list[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all users (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    users = db.query(User).offset(skip).limit(limit).all()
    return users


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    import traceback
    error_detail = str(exc)
    error_traceback = traceback.format_exc()
    
    # Log the error for debugging
    print(f"Unhandled exception: {error_detail}")
    print(f"Traceback: {error_traceback}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error", 
            "status_code": 500,
            "error": error_detail
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
