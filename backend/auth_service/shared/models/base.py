"""
Base SQLAlchemy model with common fields and methods.
"""

from datetime import datetime
from typing import Any
from sqlalchemy import Column, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

Base = declarative_base()


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps to models."""
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class BaseModel(Base, TimestampMixin):
    """Base model class that includes timestamp fields."""
    
    __abstract__ = True
    
    def to_dict(self) -> dict[str, Any]:
        """Convert model instance to dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
    
    def update(self, db: Session, **kwargs) -> "BaseModel":
        """Update model instance with new values."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        db.commit()
        db.refresh(self)
        return self
    
    @classmethod
    def get_by_id(cls, db: Session, id: Any) -> "BaseModel":
        """Get model instance by ID."""
        return db.query(cls).filter(cls.id == id).first()
    
    @classmethod
    def get_all(cls, db: Session, skip: int = 0, limit: int = 100) -> list["BaseModel"]:
        """Get all model instances with pagination."""
        return db.query(cls).offset(skip).limit(limit).all()
    
    @classmethod
    def create(cls, db: Session, **kwargs) -> "BaseModel":
        """Create new model instance."""
        instance = cls(**kwargs)
        db.add(instance)
        db.commit()
        db.refresh(instance)
        return instance
    
    def delete(self, db: Session) -> bool:
        """Delete model instance."""
        db.delete(self)
        db.commit()
        return True
