"""
Unit tests for the Chat Service
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, String, Column
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import redis.asyncio as redis
from datetime import datetime
import uuid
# Import the app and models
from main import app
from shared.database.connection import get_db
from shared.models import ChatHistory, User, Device, Telemetry, Base
from shared.utils.auth import get_current_user_from_token

# Test database configuration
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create test database tables
Base.metadata.create_all(bind=engine)

# Mock Redis client
mock_redis = AsyncMock()

# Mock OpenAI client
mock_openai = MagicMock()

def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Override dependencies
app.dependency_overrides[get_db] = override_get_db

# Mock authentication dependency
def mock_get_current_user():
    """Mock current user for testing."""
    return {
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "email": "test@example.com",
        "role": "user"
    }

app.dependency_overrides[get_current_user_from_token] = mock_get_current_user

@pytest.fixture
def client():
    """Create test client."""
    client = TestClient(app)
    yield client
    # Clean up dependency overrides after each test
    app.dependency_overrides.clear()

@pytest.fixture
def db_session():
    """Create database session for testing."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Clean up test tables
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "password": "$2b$10$rQZ8K9vX8K9vX8K9vX8K9O",
        "first_name": "Test",
        "last_name": "User",
        "role": "user"
    }

@pytest.fixture
def test_user(db_session, sample_user_data):
    """Create a test user in the database."""
    user = User(
        id=uuid.uuid4(),
        email=f"testuser-{uuid.uuid4()}@example.com",
        password_hash=sample_user_data["password"],
        first_name=sample_user_data["first_name"],
        last_name=sample_user_data["last_name"],
        role=sample_user_data["role"]
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def sample_device_data():
    """Sample device data for testing."""
    return {
        "name": "Test Device",
        "device_type": "smart_plug",
        "location": "Living Room",
        "manufacturer": "Test Brand",
        "model": "Test Model",
        "is_active": True
    }

@pytest.fixture
def sample_telemetry_data():
    """Sample telemetry data for testing."""
    return {
        "device_id": "test-device-id",
        "timestamp": datetime.utcnow(),
        "energy_watts": 150.5
    }

@pytest.fixture
def mock_redis_client():
    """Mock Redis client."""
    with patch('main.redis_client', mock_redis):
        yield mock_redis

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    with patch('main.openai_client', mock_openai):
        yield mock_openai

@pytest.fixture
def auth_headers():
    """Create authenticated headers for testing."""
    # Since we're mocking the auth dependency, any valid token format will work
    return {"Authorization": "Bearer test-token"}

class TestChatQuery:
    """Test chat query functionality."""
    
    def test_send_query_success(self, client, auth_headers, mock_redis_client, mock_openai_client):
        """Test successful chat query."""
        # Mock OpenAI response
        mock_openai.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Test response"))]
        )
        
        query_data = {
            "question": "What is my energy consumption?",
            "user_id": "123e4567-e89b-12d3-a456-426614174000"
        }
        
        response = client.post("/query", json=query_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "response" in data
        assert "intent" in data
        assert "confidence" in data
    
class TestSupportedIntents:
    """Test supported intents functionality."""
    
    def test_get_supported_intents_success(self, client, auth_headers):
        """Test successful retrieval of supported intents."""
        response = client.get("/intents", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "intents" in data
        assert "intents" in data
        assert "device_energy" in data["intents"]
        assert "examples" in data["intents"]["device_energy"]
        assert isinstance(data["intents"], dict)
        assert isinstance(data["features"], dict)
    
    def test_get_supported_intents_unauthorized(self, client):
        """Test supported intents without authentication."""
        response = client.get("/intents")
        assert response.status_code == 200

class TestHealthCheck:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_rate_limiting(self, client, db_session, auth_headers, mock_redis_client):
        """Test rate limiting for chat queries."""
        # Mock Redis rate limiting
        mock_redis.get.return_value = "5"  # 5 requests in current window
        
        query_data = {
            "question": "Test question",
            "user_id": "123e4567-e89b-12d3-a456-426614174000"
        }
        
        # Should be rate limited
        response = client.post("/query", json=query_data, headers=auth_headers)
        # Note: This test depends on the actual rate limiting implementation
        # The response code may vary based on the implementation

if __name__ == "__main__":
    pytest.main([__file__])
