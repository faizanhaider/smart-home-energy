"""
FastAPI Telemetry Service for Smart Home Energy Monitoring.
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import redis.asyncio as redis
import pandas as pd
import numpy as np

from shared.database.connection import get_db, create_tables
from shared.models import Device, Telemetry, User

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
MAX_TELEMETRY_BATCH_SIZE = int(os.getenv("MAX_TELEMETRY_BATCH_SIZE", "1000"))

# Initialize FastAPI app
app = FastAPI(
    title="Smart Home Energy - Telemetry Service",
    description="Device telemetry data ingestion and query service",
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


# Pydantic models
from pydantic import BaseModel, Field, validator


class TelemetryData(BaseModel):
    """Single telemetry data point."""
    device_id: str = Field(..., description="Device identifier")
    timestamp: datetime = Field(..., description="Timestamp of the measurement")
    energy_watts: float = Field(..., ge=0, description="Energy consumption in watts")


class TelemetryBatch(BaseModel):
    """Batch of telemetry data points."""
    data: List[TelemetryData] = Field(..., max_items=MAX_TELEMETRY_BATCH_SIZE)


class TelemetryResponse(BaseModel):
    """Telemetry response model."""
    id: str
    device_id: str
    timestamp: datetime
    energy_watts: float
    created_at: datetime
    
    class Config:
        from_attributes = True


class DeviceSummary(BaseModel):
    """Device energy consumption summary."""
    device_id: str
    device_name: str
    total_energy: float
    average_power: float
    peak_power: float
    data_points: int
    last_reading: Optional[datetime]
    
    class Config:
        from_attributes = True


class UserDevicesSummary(BaseModel):
    """Summary of all user devices."""
    user_id: str
    total_energy: float
    average_power: float
    peak_power: float
    device_count: int
    data_points: int
    devices: List[DeviceSummary]


# Utility functions
async def get_device_info(db: Session, device_id: str) -> Optional[Device]:
    """Get device information, with Redis caching."""
    if redis_client:
        try:
            cached_device = await redis_client.get(f"device:{device_id}")
            if cached_device:
                return Device(**eval(cached_device))
        except Exception:
            pass
    
    device = db.query(Device).filter(Device.id == device_id).first()
    
    if device and redis_client:
        try:
            await redis_client.setex(
                f"device:{device_id}",
                300,  # 5 minutes cache
                str(device.to_dict())
            )
        except Exception:
            pass
    
    return device


async def validate_device_access(db: Session, device_id: str, user_id: str) -> Device:
    """Validate that user has access to the device."""
    device = await get_device_info(db, device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    if device.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this device"
        )
    
    return device


# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "telemetry-service",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@app.post("/", response_model=TelemetryResponse, status_code=status.HTTP_201_CREATED)
async def create_telemetry(
    telemetry_data: TelemetryData,
    db: Session = Depends(get_db)
):
    """Create a single telemetry data point."""
    # Validate device exists
    device = await get_device_info(db, telemetry_data.device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Create telemetry record
    db_telemetry = Telemetry(
        id=str(uuid.uuid4()),
        device_id=telemetry_data.device_id,
        timestamp=telemetry_data.timestamp,
        energy_watts=telemetry_data.energy_watts
    )
    
    db.add(db_telemetry)
    db.commit()
    db.refresh(db_telemetry)
    
    # Invalidate device cache
    if redis_client:
        try:
            await redis_client.delete(f"device:{telemetry_data.device_id}")
        except Exception:
            pass
    
    return db_telemetry


@app.post("/batch", response_model=List[TelemetryResponse], status_code=status.HTTP_201_CREATED)
async def create_telemetry_batch(
    telemetry_batch: TelemetryBatch,
    db: Session = Depends(get_db)
):
    """Create multiple telemetry data points in a batch."""
    if len(telemetry_batch.data) > MAX_TELEMETRY_BATCH_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch size exceeds maximum of {MAX_TELEMETRY_BATCH_SIZE}"
        )
    
    # Validate all devices exist
    device_ids = [item.device_id for item in telemetry_batch.data]
    devices = db.query(Device).filter(Device.id.in_(device_ids)).all()
    device_map = {device.id: device for device in devices}
    
    if len(devices) != len(device_ids):
        missing_devices = set(device_ids) - set(device_map.keys())
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Devices not found: {missing_devices}"
        )
    
    # Create telemetry records
    telemetry_records = []
    for item in telemetry_batch.data:
        db_telemetry = Telemetry(
            id=str(uuid.uuid4()),
            device_id=item.device_id,
            timestamp=item.timestamp,
            energy_watts=item.energy_watts
        )
        telemetry_records.append(db_telemetry)
    
    db.add_all(telemetry_records)
    db.commit()
    
    # Refresh all records
    for record in telemetry_records:
        db.refresh(record)
    
    # Invalidate device caches
    if redis_client:
        try:
            await redis_client.delete(*[f"device:{device_id}" for device_id in device_ids])
        except Exception:
            pass
    
    return telemetry_records


@app.get("/device/{device_id}", response_model=List[TelemetryResponse])
async def get_device_telemetry(
    device_id: str,
    hours: int = 24,
    limit: int = 1000,
    db: Session = Depends(get_db)
):
    """Get telemetry data for a specific device."""
    # Validate device exists
    device = await get_device_info(db, device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Get telemetry data
    telemetry_data = Telemetry.get_device_telemetry(db, device_id, hours, limit)
    return telemetry_data


@app.get("/device/{device_id}/summary", response_model=DeviceSummary)
async def get_device_summary(
    device_id: str,
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Get energy consumption summary for a specific device."""
    # Validate device exists
    device = await get_device_info(db, device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Get summary data
    summary = device.get_energy_consumption_summary(db, hours)
    
    # Get last reading
    last_reading = db.query(Telemetry).filter(
        Telemetry.device_id == device_id
    ).order_by(Telemetry.timestamp.desc()).first()
    
    return DeviceSummary(
        device_id=device_id,
        device_name=device.name,
        total_energy=summary["total_energy"],
        average_power=summary["average_power"],
        peak_power=summary["peak_power"],
        data_points=summary["data_points"],
        last_reading=last_reading.timestamp if last_reading else None
    )


@app.get("/device/{device_id}/hourly", response_model=List[dict])
async def get_device_hourly_consumption(
    device_id: str,
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Get hourly energy consumption for a device."""
    # Validate device exists
    device = await get_device_info(db, device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Get hourly data
    hourly_data = Telemetry.get_hourly_consumption(db, device_id, hours)
    return hourly_data


@app.get("/user/{user_id}/devices", response_model=List[DeviceSummary])
async def get_user_devices_summary(
    user_id: str,
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Get energy consumption summary for all user devices."""
    # Get user devices
    devices = db.query(Device).filter(Device.user_id == user_id).all()
    
    if not devices:
        return []
    
    # Get summary for each device
    device_summaries = []
    for device in devices:
        summary = device.get_energy_consumption_summary(db, hours)
        
        # Get last reading
        last_reading = db.query(Telemetry).filter(
            Telemetry.device_id == device.id
        ).order_by(Telemetry.timestamp.desc()).first()
        
        device_summaries.append(DeviceSummary(
            device_id=device.id,
            device_name=device.name,
            total_energy=summary["total_energy"],
            average_power=summary["average_power"],
            peak_power=summary["peak_power"],
            data_points=summary["data_points"],
            last_reading=last_reading.timestamp if last_reading else None
        ))
    
    return device_summaries


@app.get("/user/{user_id}/summary", response_model=UserDevicesSummary)
async def get_user_summary(
    user_id: str,
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Get overall energy consumption summary for a user."""
    # Get user devices summary
    devices_summary = await get_user_devices_summary(user_id, hours, db)
    
    if not devices_summary:
        return UserDevicesSummary(
            user_id=user_id,
            total_energy=0,
            average_power=0,
            peak_power=0,
            device_count=0,
            data_points=0,
            devices=[]
        )
    
    # Calculate overall summary
    total_energy = sum(device.total_energy for device in devices_summary)
    total_data_points = sum(device.data_points for device in devices_summary)
    
    # Calculate weighted average power
    if total_data_points > 0:
        weighted_power = sum(
            device.average_power * device.data_points for device in devices_summary
        )
        average_power = weighted_power / total_data_points
    else:
        average_power = 0
    
    peak_power = max(device.peak_power for device in devices_summary) if devices_summary else 0
    
    return UserDevicesSummary(
        user_id=user_id,
        total_energy=total_energy,
        average_power=round(average_power, 2),
        peak_power=peak_power,
        device_count=len(devices_summary),
        data_points=total_data_points,
        devices=devices_summary
    )


@app.delete("/device/{device_id}/telemetry")
async def delete_device_telemetry(
    device_id: str,
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Delete telemetry data for a device (within specified hours)."""
    # Validate device exists
    device = await get_device_info(db, device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    # Calculate cutoff time
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    # Delete telemetry data
    deleted_count = db.query(Telemetry).filter(
        and_(
            Telemetry.device_id == device_id,
            Telemetry.timestamp >= cutoff_time
        )
    ).delete()
    
    db.commit()
    
    # Invalidate device cache
    if redis_client:
        try:
            await redis_client.delete(f"device:{device_id}")
        except Exception:
            pass
    
    return {"message": f"Deleted {deleted_count} telemetry records"}


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
        port=8001,
        reload=True,
        log_level="info"
    )
