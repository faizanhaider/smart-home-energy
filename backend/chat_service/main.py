"""
FastAPI Chat Service for Smart Home Energy Monitoring.
Handles natural language queries and returns structured responses.
"""

import os
import re
import time
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import redis.asyncio as redis
import httpx
from textblob import TextBlob
import nltk

from ..shared.database.connection import get_db, create_tables
from ..shared.models import ChatHistory, User, Device, Telemetry

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8000")
TELEMETRY_SERVICE_URL = os.getenv("TELEMETRY_SERVICE_URL", "http://localhost:8001")

# Initialize FastAPI app
app = FastAPI(
    title="Smart Home Energy - Chat Service",
    description="Natural language query processing and AI responses",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT") == "development" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") == "development" else None
)

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


# Natural Language Processing Functions
class QueryIntent:
    """Class to handle query intent detection and processing."""
    
    # Intent patterns
    INTENT_PATTERNS = {
        "device_energy": [
            r"how much energy did (?:my )?(\w+)(?:\s+\w+)* use",
            r"energy consumption of (?:my )?(\w+)(?:\s+\w+)*",
            r"power usage of (?:my )?(\w+)(?:\s+\w+)*",
            r"(\w+)(?:\s+\w+)* energy consumption"
        ],
        "device_comparison": [
            r"which (?:of my )?devices? (?:are|is) using the most power",
            r"top (\d+) energy consuming devices",
            r"highest power consuming device",
            r"compare energy usage of my devices"
        ],
        "time_period": [
            r"(?:energy|power) (?:usage|consumption) (?:in|for|over) the last (\w+)",
            r"(\w+) energy consumption",
            r"energy usage (?:for|in) (\w+)"
        ],
        "total_consumption": [
            r"total energy consumption",
            r"overall power usage",
            r"total electricity usage",
            r"sum of all devices energy"
        ],
        "device_status": [
            r"is (?:my )?(\w+)(?:\s+\w+)* (?:on|off|active)",
            r"status of (?:my )?(\w+)(?:\s+\w+)*",
            r"(\w+)(?:\s+\w+)* status"
        ]
    }
    
    # Time period mappings
    TIME_PERIODS = {
        "hour": 1,
        "day": 24,
        "week": 168,
        "month": 720,
        "year": 8760,
        "today": 24,
        "yesterday": 24,
        "last week": 168,
        "last month": 720
    }
    
    @classmethod
    def detect_intent(cls, query: str) -> Dict[str, Any]:
        """Detect the intent and extract parameters from a natural language query."""
        query_lower = query.lower().strip()
        
        # Initialize result
        result = {
            "intent": "unknown",
            "confidence": 0.0,
            "parameters": {},
            "entities": {}
        }
        
        # Check each intent pattern
        for intent, patterns in cls.INTENT_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, query_lower)
                if matches:
                    result["intent"] = intent
                    result["confidence"] = 0.8
                    
                    # Extract parameters based on intent
                    if intent == "device_energy":
                        result["entities"]["device_name"] = matches[0]
                    elif intent == "device_comparison":
                        if "top" in query_lower:
                            # Extract number for top N devices
                            num_match = re.search(r"top (\d+)", query_lower)
                            if num_match:
                                result["parameters"]["limit"] = int(num_match.group(1))
                            else:
                                result["parameters"]["limit"] = 3
                    elif intent == "time_period":
                        time_period = matches[0]
                        result["parameters"]["hours"] = cls.TIME_PERIODS.get(time_period, 24)
                    
                    break
            
            if result["intent"] != "unknown":
                break
        
        # Extract time-related keywords
        time_keywords = {
            "now": 0,
            "current": 0,
            "recent": 1,
            "last hour": 1,
            "last day": 24,
            "last week": 168,
            "last month": 720
        }
        
        for keyword, hours in time_keywords.items():
            if keyword in query_lower:
                result["parameters"]["hours"] = hours
                break
        
        # If no specific time period found, default to 24 hours
        if "hours" not in result["parameters"]:
            result["parameters"]["hours"] = 24
        
        return result
    
    @classmethod
    def extract_device_name(cls, query: str) -> Optional[str]:
        """Extract device name from query using NLP."""
        blob = TextBlob(query)
        
        # Look for nouns that might be device names
        for word, tag in blob.tags:
            if tag.startswith('NN') and len(word) > 2:
                # Common device keywords
                device_keywords = [
                    'fridge', 'refrigerator', 'ac', 'air', 'conditioner', 'light',
                    'computer', 'laptop', 'tv', 'television', 'washer', 'dryer',
                    'dishwasher', 'microwave', 'oven', 'stove', 'heater', 'fan'
                ]
                
                if word.lower() in device_keywords:
                    return word
        
        return None


# Pydantic models
from pydantic import BaseModel, Field


class ChatQuery(BaseModel):
    """Chat query model."""
    question: str = Field(..., min_length=1, max_length=500, description="Natural language question")
    user_id: Optional[str] = Field(None, description="User ID for authenticated queries")


class ChatResponse(BaseModel):
    """Chat response model."""
    id: str
    question: str
    response: Dict[str, Any]
    intent: str
    confidence: float
    processing_time_ms: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class QueryResult(BaseModel):
    """Query result model."""
    summary: str
    data: Optional[Dict[str, Any]] = None
    charts: Optional[List[Dict[str, Any]]] = None
    recommendations: Optional[List[str]] = None


# Utility functions
async def get_user_devices(db: Session, user_id: str) -> List[Device]:
    """Get all devices for a user."""
    return db.query(Device).filter(Device.user_id == user_id).all()


async def get_device_by_name(db: Session, user_id: str, device_name: str) -> Optional[Device]:
    """Find device by name for a specific user."""
    devices = await get_user_devices(db, user_id)
    
    # Simple fuzzy matching
    device_name_lower = device_name.lower()
    for device in devices:
        if device_name_lower in device.name.lower() or device_name_lower in device.device_type.lower():
            return device
    
    return None


async def query_telemetry_service(device_id: str, hours: int) -> Dict[str, Any]:
    """Query telemetry service for device data."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{TELEMETRY_SERVICE_URL}/device/{device_id}/summary",
                params={"hours": hours}
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error querying telemetry service: {e}")
    
    return {}


async def get_user_summary(db: Session, user_id: str, hours: int) -> Dict[str, Any]:
    """Get overall user energy consumption summary."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{TELEMETRY_SERVICE_URL}/user/{user_id}/summary",
                params={"hours": hours}
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error querying telemetry service: {e}")
    
    return {}


# Query processing functions
async def process_device_energy_query(
    db: Session, 
    user_id: str, 
    device_name: str, 
    hours: int
) -> QueryResult:
    """Process device energy consumption query."""
    device = await get_device_by_name(db, user_id, device_name)
    
    if not device:
        return QueryResult(
            summary=f"I couldn't find a device named '{device_name}' in your smart home setup.",
            recommendations=[
                "Check the device name spelling",
                "Verify the device is registered in your account",
                "Try using a different device name"
            ]
        )
    
    # Get device telemetry data
    telemetry_data = await query_telemetry_service(device.id, hours)
    
    if not telemetry_data:
        return QueryResult(
            summary=f"I found your {device.name} but couldn't retrieve energy data for the last {hours} hours.",
            recommendations=[
                "Check if the device is currently active",
                "Verify the device is sending telemetry data",
                "Try a different time period"
            ]
        )
    
    # Format response
    time_period = f"last {hours} hours" if hours > 1 else "last hour"
    summary = (
        f"Your {device.name} consumed {telemetry_data.get('total_energy', 0):.2f} watts "
        f"over the {time_period}. "
        f"The average power consumption was {telemetry_data.get('average_power', 0):.2f} watts, "
        f"with a peak of {telemetry_data.get('peak_power', 0):.2f} watts."
    )
    
    return QueryResult(
        summary=summary,
        data={
            "device_name": device.name,
            "device_type": device.device_type,
            "total_energy": telemetry_data.get('total_energy', 0),
            "average_power": telemetry_data.get('average_power', 0),
            "peak_power": telemetry_data.get('peak_power', 0),
            "data_points": telemetry_data.get('data_points', 0)
        }
    )


async def process_device_comparison_query(
    db: Session, 
    user_id: str, 
    hours: int,
    limit: int = 3
) -> QueryResult:
    """Process device comparison query."""
    # Get user devices summary
    user_summary = await get_user_summary(db, user_id, hours)
    
    if not user_summary or not user_summary.get('devices'):
        return QueryResult(
            summary="I couldn't find any devices or energy data to compare.",
            recommendations=[
                "Make sure you have devices registered",
                "Check if devices are sending telemetry data",
                "Try a different time period"
            ]
        )
    
    # Sort devices by total energy consumption
    devices = sorted(
        user_summary['devices'], 
        key=lambda x: x['total_energy'], 
        reverse=True
    )[:limit]
    
    # Format response
    time_period = f"last {hours} hours" if hours > 1 else "last hour"
    summary = f"Here are your top {len(devices)} energy-consuming devices over the {time_period}:\n\n"
    
    for i, device in enumerate(devices, 1):
        summary += f"{i}. {device['device_name']}: {device['total_energy']:.2f} watts\n"
    
    summary += f"\nTotal energy consumption: {user_summary.get('total_energy', 0):.2f} watts"
    
    return QueryResult(
        summary=summary,
        data={
            "top_devices": devices,
            "total_energy": user_summary.get('total_energy', 0),
            "device_count": len(devices)
        }
    )


async def process_total_consumption_query(
    db: Session, 
    user_id: str, 
    hours: int
) -> QueryResult:
    """Process total energy consumption query."""
    user_summary = await get_user_summary(db, user_id, hours)
    
    if not user_summary:
        return QueryResult(
            summary="I couldn't retrieve your total energy consumption data.",
            recommendations=[
                "Check if you have devices registered",
                "Verify devices are sending telemetry data",
                "Try a different time period"
            ]
        )
    
    time_period = f"last {hours} hours" if hours > 1 else "last hour"
    summary = (
        f"Your total energy consumption over the {time_period} is "
        f"{user_summary.get('total_energy', 0):.2f} watts. "
        f"You have {user_summary.get('device_count', 0)} active devices, "
        f"with an average power consumption of {user_summary.get('average_power', 0):.2f} watts."
    )
    
    return QueryResult(
        summary=summary,
        data=user_summary
    )


# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "chat-service",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@app.post("/query", response_model=ChatResponse)
async def process_chat_query(
    chat_query: ChatQuery,
    db: Session = Depends(get_db)
):
    """Process a natural language query and return a structured response."""
    start_time = time.time()
    
    # Detect intent
    intent_result = QueryIntent.detect_intent(chat_query.question)
    
    # Process query based on intent
    if intent_result["intent"] == "device_energy":
        device_name = intent_result["entities"].get("device_name", "unknown")
        hours = intent_result["parameters"].get("hours", 24)
        result = await process_device_energy_query(db, chat_query.user_id, device_name, hours)
    
    elif intent_result["intent"] == "device_comparison":
        hours = intent_result["parameters"].get("hours", 24)
        limit = intent_result["parameters"].get("limit", 3)
        result = await process_device_comparison_query(db, chat_query.user_id, hours, limit)
    
    elif intent_result["intent"] == "total_consumption":
        hours = intent_result["parameters"].get("hours", 24)
        result = await process_total_consumption_query(db, chat_query.user_id, hours)
    
    else:
        result = QueryResult(
            summary="I'm not sure how to help with that question. Try asking about your device energy consumption, comparing devices, or getting total energy usage.",
            recommendations=[
                "Ask about specific device energy usage: 'How much energy did my fridge use yesterday?'",
                "Compare devices: 'Which of my devices are using the most power?'",
                "Get total consumption: 'What's my total energy consumption this week?'"
            ]
        )
    
    # Calculate processing time
    processing_time = int((time.time() - start_time) * 1000)
    
    # Create chat history record
    chat_record = ChatHistory(
        id=str(uuid.uuid4()),
        user_id=chat_query.user_id or "anonymous",
        question=chat_query.question,
        response=result.dict(),
        intent=intent_result["intent"],
        confidence=str(intent_result["confidence"]),
        processing_time_ms=str(processing_time)
    )
    
    db.add(chat_record)
    db.commit()
    db.refresh(chat_record)
    
    return chat_record


@app.get("/history", response_model=List[ChatResponse])
async def get_chat_history(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get chat history for a user."""
    chat_history = ChatHistory.get_user_chat_history(db, user_id, limit, offset)
    return chat_history


@app.get("/intents")
async def get_supported_intents():
    """Get list of supported query intents and examples."""
    return {
        "intents": {
            "device_energy": {
                "description": "Query energy consumption of a specific device",
                "examples": [
                    "How much energy did my fridge use yesterday?",
                    "What's the power usage of my AC?",
                    "Energy consumption of my computer"
                ]
            },
            "device_comparison": {
                "description": "Compare energy usage across devices",
                "examples": [
                    "Which of my devices are using the most power?",
                    "Top 3 energy-consuming devices",
                    "Compare energy usage of my devices"
                ]
            },
            "total_consumption": {
                "description": "Get overall energy consumption summary",
                "examples": [
                    "What's my total energy consumption this week?",
                    "Overall power usage for today",
                    "Sum of all devices energy"
                ]
            }
        },
        "time_periods": ["hour", "day", "week", "month", "today", "yesterday", "last week", "last month"]
    }


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
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "status_code": 500}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )
