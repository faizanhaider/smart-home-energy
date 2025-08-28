"""
FastAPI Chat Service for Smart Home Energy Monitoring.
Handles natural language queries and returns structured responses with OpenAI integration.
"""

import os
import re
import time
import uuid
import json
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
import openai
from openai import OpenAI

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from shared.database.connection import get_db, create_tables
from shared.models import ChatHistory, User, Device, Telemetry
from shared.utils.auth import get_current_user_from_token, get_current_user_id, require_admin

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8000")
TELEMETRY_SERVICE_URL = os.getenv("TELEMETRY_SERVICE_URL", "http://localhost:8001")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
ENABLE_OPENAI = os.getenv("ENABLE_OPENAI", "true").lower() == "true"

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

# OpenAI client
openai_client: Optional[OpenAI] = None

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
    global redis_client, openai_client
    
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
    
    # Initialize OpenAI client
    if ENABLE_OPENAI and OPENAI_API_KEY:
        try:
            openai_client = OpenAI(api_key=OPENAI_API_KEY)
            # Test the connection
            response = openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            print("✅ OpenAI connected successfully")
        except Exception as e:
            print(f"⚠️  OpenAI connection failed: {e}")
            openai_client = None
    else:
        print("⚠️  OpenAI disabled or API key not provided")
        openai_client = None


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    if redis_client:
        await redis_client.close()
    
    # OpenAI client doesn't need explicit cleanup
    global openai_client
    openai_client = None


# Natural Language Processing Functions
class QueryIntent:
    """Class to handle query intent detection and processing with OpenAI integration."""
    
    # Intent patterns for fallback when OpenAI is not available
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
    async def detect_intent_with_openai(cls, query: str) -> Dict[str, Any]:
        """Use OpenAI to detect intent and extract parameters."""
        if not openai_client:
            return None
        
        try:
            system_prompt = """You are an AI assistant that helps users understand their smart home energy consumption. 
            Analyze the user's question and return a JSON response with the following structure:
            {
                "intent": "device_energy|device_comparison|total_consumption|device_status|energy_analysis|cost_analysis",
                "confidence": 0.0-1.0,
                "parameters": {
                    "hours": number,
                    "limit": number,
                    "include_breakdown": boolean,
                    "include_charts": boolean
                },
                "entities": {
                    "device_name": "string",
                    "device_type": "string",
                    "time_period": "string",
                    "metric": "string"
                },
                "analysis_type": "summary|detailed|trend|comparison"
            }
            
            Intent types:
            - device_energy: Questions about specific device energy usage
            - device_comparison: Comparing energy usage across devices
            - total_consumption: Overall household energy consumption
            - device_status: Device operational status
            - energy_analysis: Detailed energy analysis and insights
            - cost_analysis: Energy cost calculations
            
            Extract time periods and convert to hours:
            - "yesterday" = 24
            - "last week" = 168
            - "last month" = 720
            - "today" = 24
            - "this week" = 168
            - "this month" = 720
            
            Be specific and accurate. Only return valid JSON."""
            
            user_prompt = f"Analyze this energy consumption question: '{query}'"
            
            response = openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            content = response.choices[0].message.content.strip()
            
            # Try to extract JSON from the response
            try:
                # Find JSON content between backticks or just parse the whole response
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    json_content = content[json_start:json_end].strip()
                elif "```" in content:
                    json_start = content.find("```") + 3
                    json_end = content.find("```", json_start)
                    json_content = content[json_start:json_end].strip()
                else:
                    json_content = content
                
                result = json.loads(json_content)
                
                # Validate and normalize the result
                if "intent" not in result:
                    result["intent"] = "unknown"
                if "confidence" not in result:
                    result["confidence"] = 0.8
                if "parameters" not in result:
                    result["parameters"] = {}
                if "entities" not in result:
                    result["entities"] = {}
                
                # Ensure hours parameter is set
                if "hours" not in result["parameters"]:
                    result["parameters"]["hours"] = 24
                
                return result
                
            except json.JSONDecodeError as e:
                print(f"Failed to parse OpenAI response as JSON: {e}")
                return None
                
        except Exception as e:
            print(f"OpenAI intent detection failed: {e}")
            return None
    
    @classmethod
    async def detect_intent(cls, query: str) -> Dict[str, Any]:
        """Detect the intent and extract parameters from a natural language query."""
        # Try OpenAI first if available
        if openai_client:
            openai_result = await cls.detect_intent_with_openai(query)
            if openai_result:
                return openai_result
        
        # Fallback to rule-based detection
        return cls._detect_intent_rule_based(query)
    
    @classmethod
    def _detect_intent_rule_based(cls, query: str) -> Dict[str, Any]:
        """Fallback rule-based intent detection."""
        query_lower = query.lower().strip()
        
        # Initialize result
        result = {
            "intent": "unknown",
            "confidence": 0.6,  # Lower confidence for rule-based
            "parameters": {},
            "entities": {}
        }
        
        # Check each intent pattern
        for intent, patterns in cls.INTENT_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, query_lower)
                if matches:
                    result["intent"] = intent
                    result["confidence"] = 0.6
                    
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
    user_id: Optional[uuid.UUID] = Field(None, description="User ID for authenticated queries")


class ChatResponse(BaseModel):
    """Chat response model."""
    id: uuid.UUID
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
    hours: int,
    include_breakdown: bool = False
) -> QueryResult:
    """Process device energy consumption query with enhanced analysis."""
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
    
    # Enhanced summary with insights
    total_energy = telemetry_data.get('total_energy', 0)
    avg_power = telemetry_data.get('average_power', 0)
    peak_power = telemetry_data.get('peak_power', 0)
    
    # Calculate energy efficiency insights
    efficiency_rating = "efficient" if avg_power < 100 else "moderate" if avg_power < 500 else "high consumption"
    
    summary = (
        f"Your {device.name} consumed {total_energy:.2f} watts over the {time_period}. "
        f"The average power consumption was {avg_power:.2f} watts, "
        f"with a peak of {peak_power:.2f} watts. "
        f"This device shows {efficiency_rating} energy usage patterns."
    )
    
    # Add cost estimation if we have energy data
    if total_energy > 0:
        # Rough cost calculation (assuming $0.12 per kWh)
        cost_per_kwh = 0.12
        energy_kwh = total_energy / 1000  # Convert watts to kWh
        estimated_cost = energy_kwh * cost_per_kwh
        summary += f" Estimated cost: ${estimated_cost:.2f}"
    
    result_data = {
        "device_name": device.name,
        "device_type": device.device_type,
        "total_energy": total_energy,
        "average_power": avg_power,
        "peak_power": peak_power,
        "data_points": telemetry_data.get('data_points', 0),
        "efficiency_rating": efficiency_rating,
        "time_period_hours": hours
    }
    
    # Add hourly breakdown if requested
    if include_breakdown:
        hourly_data = await get_device_hourly_consumption(db, device.id, hours)
        result_data["hourly_breakdown"] = hourly_data
        summary += " I've included an hourly breakdown of your energy consumption."
    
    return QueryResult(
        summary=summary,
        data=result_data
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
    total_energy = user_summary.get('total_energy', 0)
    avg_power = user_summary.get('average_power', 0)
    device_count = user_summary.get('device_count', 0)
    
    # Enhanced summary with insights
    summary = (
        f"Your total energy consumption over the {time_period} is "
        f"{total_energy:.2f} watts. "
        f"You have {device_count} active devices, "
        f"with an average power consumption of {avg_power:.2f} watts."
    )
    
    # Add cost and efficiency insights
    if total_energy > 0:
        cost_per_kwh = 0.12
        energy_kwh = total_energy / 1000
        estimated_cost = energy_kwh * cost_per_kwh
        
        # Calculate per-device average
        per_device_avg = total_energy / device_count if device_count > 0 else 0
        
        summary += (
            f" Estimated cost: ${estimated_cost:.2f}. "
            f"Average consumption per device: {per_device_avg:.2f} watts."
        )
    
    return QueryResult(
        summary=summary,
        data=user_summary
    )

async def process_energy_analysis_query(
    db: Session, 
    user_id: str, 
    hours: int,
    analysis_type: str = "summary"
) -> QueryResult:
    """Process detailed energy analysis query."""
    user_summary = await get_user_summary(db, user_id, hours)
    
    if not user_summary:
        return QueryResult(
            summary="I couldn't retrieve energy analysis data.",
            recommendations=[
                "Check if you have devices registered",
                "Verify devices are sending telemetry data",
                "Try a different time period"
            ]
        )
    
    # Get detailed device breakdown
    devices_summary = await get_user_devices_summary(db, user_id, hours)
    
    if not devices_summary:
        return QueryResult(
            summary="No device data available for analysis.",
            data=user_summary
        )
    
    # Perform detailed analysis
    total_energy = user_summary.get('total_energy', 0)
    device_count = len(devices_summary)
    
    # Sort devices by energy consumption
    sorted_devices = sorted(devices_summary, key=lambda x: x.total_energy, reverse=True)
    
    # Calculate insights
    top_consumer = sorted_devices[0] if sorted_devices else None
    bottom_consumer = sorted_devices[-1] if sorted_devices else None
    
    # Energy efficiency analysis
    high_consumption_devices = [d for d in sorted_devices if d.total_energy > 1000]
    efficient_devices = [d for d in sorted_devices if d.total_energy < 100]
    
    summary = f"Energy Analysis for the last {hours} hours:\n\n"
    summary += f"📊 Total Consumption: {total_energy:.2f} watts\n"
    summary += f"🔌 Active Devices: {device_count}\n"
    
    if top_consumer:
        summary += f"🔥 Highest Consumer: {top_consumer.device_name} ({top_consumer.total_energy:.2f} watts)\n"
    
    if bottom_consumer:
        summary += f"💡 Most Efficient: {bottom_consumer.device_name} ({bottom_consumer.total_energy:.2f} watts)\n"
    
    if high_consumption_devices:
        summary += f"⚠️  High Consumption Devices: {len(high_consumption_devices)}\n"
    
    if efficient_devices:
        summary += f"✅ Efficient Devices: {len(efficient_devices)}\n"
    
    # Add recommendations
    recommendations = []
    if high_consumption_devices:
        recommendations.append("Consider optimizing high-consumption devices during peak hours")
    
    if total_energy > 5000:  # High total consumption
        recommendations.append("Your overall energy usage is high - consider energy-saving measures")
    
    if device_count > 10:
        recommendations.append("You have many devices - consider consolidating or scheduling usage")
    
    analysis_data = {
        "total_energy": total_energy,
        "device_count": device_count,
        "top_consumers": sorted_devices[:3],
        "efficiency_breakdown": {
            "high_consumption": len(high_consumption_devices),
            "moderate_consumption": len(sorted_devices) - len(high_consumption_devices) - len(efficient_devices),
            "efficient": len(efficient_devices)
        },
        "device_rankings": sorted_devices,
        "recommendations": recommendations
    }
    
    return QueryResult(
        summary=summary,
        data=analysis_data,
        recommendations=recommendations
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
    current_user: Dict = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    if current_user['user_id'] != str(chat_query.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden"
        )

    """Process a natural language query and return a structured response."""
    start_time = time.time()
    
    # Detect intent
    intent_result = await QueryIntent.detect_intent(chat_query.question)
    
    # Process query based on intent
    if intent_result["intent"] == "device_energy":
        device_name = intent_result["entities"].get("device_name", "unknown")
        hours = intent_result["parameters"].get("hours", 24)
        include_breakdown = intent_result["parameters"].get("include_breakdown", False)
        result = await process_device_energy_query(db, chat_query.user_id, device_name, hours, include_breakdown)
    
    elif intent_result["intent"] == "device_comparison":
        hours = intent_result["parameters"].get("hours", 24)
        limit = intent_result["parameters"].get("limit", 3)
        result = await process_device_comparison_query(db, chat_query.user_id, hours, limit)
    
    elif intent_result["intent"] == "total_consumption":
        hours = intent_result["parameters"].get("hours", 24)
        result = await process_total_consumption_query(db, chat_query.user_id, hours)
    
    elif intent_result["intent"] == "energy_analysis":
        hours = intent_result["parameters"].get("hours", 24)
        analysis_type = intent_result["parameters"].get("analysis_type", "summary")
        result = await process_energy_analysis_query(db, chat_query.user_id, hours, analysis_type)
    
    elif intent_result["intent"] == "cost_analysis":
        hours = intent_result["parameters"].get("hours", 24)
        result = await process_total_consumption_query(db, chat_query.user_id, hours)
        # Enhance with cost-specific insights
        if result.data and result.data.get("total_energy", 0) > 0:
            cost_per_kwh = 0.12
            energy_kwh = result.data["total_energy"] / 1000
            estimated_cost = energy_kwh * cost_per_kwh
            result.summary += f" Cost analysis: ${estimated_cost:.2f} for this period."
    
    else:
        result = QueryResult(
            summary="I'm not sure how to help with that question. Try asking about your device energy consumption, comparing devices, or getting detailed energy analysis.",
            recommendations=[
                "Ask about specific device energy usage: 'How much energy did my AC use last week?'",
                "Compare devices: 'Which of my devices are using the most power today?'",
                "Get detailed analysis: 'Give me an energy analysis for this month'",
                "Cost analysis: 'What's my energy cost for this week?'"
            ]
        )
    
    # Calculate processing time
    processing_time = int((time.time() - start_time) * 1000)
    
    # Create chat history record
    chat_record = ChatHistory(
        id=uuid.uuid4(),
        user_id=current_user["user_id"],
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
    limit: int = 50,
    offset: int = 0,
    current_user: Dict = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """Get chat history for the current user."""
    chat_history = ChatHistory.get_user_chat_history(db, current_user["user_id"], limit, offset)
    return chat_history


@app.get("/intents")
async def get_supported_intents():
    """Get list of supported query intents and examples."""
    return {
        "intents": {
            "device_energy": {
                "description": "Query energy consumption of a specific device",
                "examples": [
                    "How much energy did my AC use last week?",
                    "What's the power usage of my fridge today?",
                    "Energy consumption of my computer yesterday"
                ]
            },
            "device_comparison": {
                "description": "Compare energy usage across devices",
                "examples": [
                    "Which of my devices are using the most power?",
                    "Top 3 energy-consuming devices today",
                    "Compare energy usage of my devices this week"
                ]
            },
            "total_consumption": {
                "description": "Get overall energy consumption summary",
                "examples": [
                    "What's my total energy consumption this week?",
                    "Overall power usage for today",
                    "Sum of all devices energy this month"
                ]
            },
            "energy_analysis": {
                "description": "Get detailed energy analysis and insights",
                "examples": [
                    "Give me an energy analysis for this month",
                    "Analyze my energy consumption patterns",
                    "What are my energy efficiency insights?"
                ]
            },
            "cost_analysis": {
                "description": "Get energy cost calculations and estimates",
                "examples": [
                    "What's my energy cost for this week?",
                    "How much did I spend on electricity today?",
                    "Calculate my energy costs for this month"
                ]
            }
        },
        "time_periods": ["hour", "day", "week", "month", "today", "yesterday", "last week", "last month"],
        "features": {
            "openai_integration": ENABLE_OPENAI and openai_client is not None,
            "cost_calculations": True,
            "efficiency_insights": True,
            "hourly_breakdowns": True,
            "smart_recommendations": True
        },
        "ai_capabilities": [
            "Natural language understanding",
            "Context-aware responses",
            "Smart intent detection",
            "Energy efficiency insights",
            "Cost optimization suggestions"
        ]
    }

@app.get("/openai/status")
async def get_openai_status():
    """Get OpenAI integration status and test connection."""
    if not ENABLE_OPENAI:
        return {
            "status": "disabled",
            "message": "OpenAI integration is disabled",
            "reason": "ENABLE_OPENAI environment variable is set to false"
        }
    
    if not OPENAI_API_KEY:
        return {
            "status": "error",
            "message": "OpenAI API key not configured",
            "reason": "OPENAI_API_KEY environment variable is not set"
        }
    
    if not openai_client:
        return {
            "status": "error",
            "message": "OpenAI client not initialized",
            "reason": "Failed to initialize OpenAI client"
        }
    
    # Test OpenAI connection
    try:
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        return {
            "status": "connected",
            "message": "OpenAI integration is working",
            "model": OPENAI_MODEL,
            "test_response": response.choices[0].message.content,
            "capabilities": [
                "Enhanced intent detection",
                "Natural language understanding",
                "Context-aware responses",
                "Smart query interpretation"
            ]
        }
    except Exception as e:
        return {
            "status": "error",
            "message": "OpenAI connection test failed",
            "reason": str(e),
            "model": OPENAI_MODEL
        }

@app.post("/openai/test")
async def test_openai_intent_detection(test_query: str):
    """Test OpenAI intent detection with a sample query."""
    if not openai_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI client not available"
        )
    
    try:
        intent_result = await QueryIntent.detect_intent_with_openai(test_query)
        if intent_result:
            return {
                "query": test_query,
                "intent_detection": intent_result,
                "success": True
            }
        else:
            return {
                "query": test_query,
                "intent_detection": None,
                "success": False,
                "message": "Failed to detect intent"
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OpenAI intent detection failed: {str(e)}"
        )

@app.get("/openai/sample-queries")
async def get_sample_queries():
    """Get sample queries to test OpenAI integration."""
    return {
        "sample_queries": [
            "How much energy did my AC use last week?",
            "What's my highest-consuming device today?",
            "Compare energy usage of my devices this month",
            "Give me an energy analysis for this week",
            "What's my energy cost for today?",
            "Which devices are most efficient?",
            "Show me energy consumption patterns",
            "What's the total power usage yesterday?"
        ],
        "testing_tips": [
            "Use /openai/status to check connection",
            "Use /openai/test with POST method and query parameter",
            "Test with natural language questions",
            "Check both OpenAI and rule-based fallback"
        ]
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
