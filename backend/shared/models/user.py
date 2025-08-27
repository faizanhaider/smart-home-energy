"""
User model for authentication and user management.
"""

from datetime import datetime
from sqlalchemy import Column, String, Boolean, Text, func, UUID
from sqlalchemy.orm import relationship
from .base import BaseModel


class User(BaseModel):
    """User model for authentication and user management."""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=func.gen_random_uuid())
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    role = Column(String(50), default="user")
    is_active = Column(Boolean, default=True)
    profile_picture = Column(Text)
    
    # Relationships
    devices = relationship("Device", back_populates="user", cascade="all, delete-orphan")
    chat_history = relationship("ChatHistory", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        return self.email
    
    def to_dict(self, include_password: bool = False) -> dict:
        """Convert user to dictionary, optionally excluding password."""
        user_dict = super().to_dict()
        if not include_password:
            user_dict.pop("password_hash", None)
        
        # Ensure datetime objects are properly serialized
        for key, value in user_dict.items():
            if isinstance(value, datetime):
                user_dict[key] = value.isoformat()
        
        return user_dict
    
    def to_json(self, include_password: bool = False) -> str:
        """Convert user to JSON string, optionally excluding password."""
        import json
        user_dict = self.to_dict(include_password)
        return json.dumps(user_dict, default=str)
