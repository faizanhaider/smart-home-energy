"""
Chat history model for storing user queries and AI responses.
"""

from sqlalchemy import Column, String, Text, ForeignKey, JSON, UUID, func
from sqlalchemy.orm import relationship
from .base import BaseModel


class ChatHistory(BaseModel):
    """Chat history model for storing user queries and AI responses."""
    
    __tablename__ = "chat_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=func.gen_random_uuid())
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    response = Column(JSON, nullable=False)
    intent = Column(String(100))  # Detected intent from the question
    confidence = Column(String(10))  # Confidence score of intent detection
    processing_time_ms = Column(String(20))  # Time taken to process the query
    
    # Relationships
    user = relationship("User", back_populates="chat_history")
    
    def __repr__(self):
        return f"<ChatHistory(user_id={self.user_id}, question={self.question[:50]}...)>"
    
    @classmethod
    def get_user_chat_history(cls, db, user_id: str, limit: int = 50, offset: int = 0):
        """Get chat history for a specific user with pagination."""
        return db.query(cls).filter(
            cls.user_id == user_id
        ).order_by(
            cls.created_at.desc()
        ).offset(offset).limit(limit).all()
    
    @classmethod
    def get_chat_statistics(cls, db, user_id: str, days: int = 30):
        """Get chat statistics for a user over the last N days."""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get chat history within the date range
        recent_chats = db.query(cls).filter(
            cls.user_id == user_id,
            cls.created_at >= cutoff_date
        ).all()
        
        if not recent_chats:
            return {
                "total_queries": 0,
                "average_processing_time": 0,
                "most_common_intent": None,
                "total_queries": 0
            }
        
        # Calculate statistics
        total_queries = len(recent_chats)
        
        # Calculate average processing time
        processing_times = []
        for chat in recent_chats:
            if chat.processing_time_ms:
                try:
                    processing_times.append(float(chat.processing_time_ms))
                except (ValueError, TypeError):
                    continue
        
        average_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        # Find most common intent
        intent_counts = {}
        for chat in recent_chats:
            if chat.intent:
                intent_counts[chat.intent] = intent_counts.get(chat.intent, 0) + 1
        
        most_common_intent = max(intent_counts.items(), key=lambda x: x[1])[0] if intent_counts else None
        
        return {
            "total_queries": total_queries,
            "average_processing_time": round(average_processing_time, 2),
            "most_common_intent": most_common_intent,
            "intent_distribution": intent_counts
        }
    
    def to_dict(self) -> dict:
        """Convert chat history to dictionary."""
        chat_dict = super().to_dict()
        
        # Ensure response is serializable
        if isinstance(chat_dict.get('response'), dict):
            chat_dict['response'] = dict(chat_dict['response'])
        
        return chat_dict
