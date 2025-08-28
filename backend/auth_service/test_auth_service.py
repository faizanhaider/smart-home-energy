"""
Unit tests for Authentication Service.

This test file focuses on testing core functionality without complex database setup.
"""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import the app and database dependency
from main import app
from shared.database.connection import get_db

# Test database configuration - use in-memory SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Mock Redis client
mock_redis = AsyncMock()

def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Override dependencies
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def client():
    """Create a test client."""
    client = TestClient(app)
    yield client
    # Clean up dependency overrides after each test
    app.dependency_overrides.clear()

@pytest.fixture
def db_session():
    """Create a test database session."""
    # Create tables
    from shared.models import Base
    Base.metadata.create_all(bind=engine)
    
    # Create session
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop tables
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "first_name": "Test",
        "last_name": "User",
        "role": "user"
    }

@pytest.fixture
def mock_redis_client():
    """Mock Redis client."""
    with patch('main.redis_client', mock_redis):
        yield mock_redis

class TestHealthCheck:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

class TestUserRegistration:
    """Test user registration functionality."""
    
    def test_register_user_success(self, client, db_session):
        """Test successful user registration."""
        response = client.post("/register", json={
            "email": f"testuser_{__import__('uuid').uuid4()}@example.com",
            "password": "testpassword123",
        })
        assert response.status_code == 201
        
        data = response.json()
        assert "id" in data
        assert "password" not in data  # Password should not be returned
    
    def test_register_user_invalid_email(self, client, db_session):
        """Test registration with invalid email."""
        invalid_data = {
            "email": "invalid-email",
            "password": "testpassword123",
            "first_name": "Test",
            "last_name": "User",
            "role": "user"
        }
        
        response = client.post("/register", json=invalid_data)
        assert response.status_code == 422

class TestUserLogin:
    """Test user login functionality."""
    
    def test_login_success(self, client, db_session, sample_user_data, mock_redis_client):
        """Test successful user login."""
        # Register user first
        client.post("/register", json=sample_user_data)
        
        # Login
        login_data = {
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        }
        
        response = client.post("/login", json=login_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    def test_login_invalid_credentials(self, client, db_session, sample_user_data):
        """Test login with invalid credentials."""
        # Register user first
        client.post("/register", json=sample_user_data)
        
        # Login with wrong password
        login_data = {
            "email": sample_user_data["email"],
            "password": "wrongpassword"
        }
        
        response = client.post("/login", json=login_data)
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
    
    def test_login_nonexistent_user(self, client, db_session):
        """Test login with nonexistent user."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "password123"
        }
        
        response = client.post("/login", json=login_data)
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

class TestTokenVerification:
    """Test JWT token verification."""
    
    def test_verify_token_invalid(self, client):
        """Test token verification with invalid token."""
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.post("/verify-token", headers=headers)
        assert response.status_code == 401
    
    def test_verify_token_missing(self, client):
        """Test token verification without token."""
        response = client.post("/verify-token")
        assert response.status_code == 401

if __name__ == "__main__":
    pytest.main([__file__])
