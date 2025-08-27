"""
Telemetry model for storing device energy consumption data.
"""

from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base import BaseModel


class Telemetry(BaseModel):
    """Telemetry model for device energy consumption data."""
    
    __tablename__ = "telemetry"
    
    id = Column(String(36), primary_key=True, index=True)
    device_id = Column(String(36), ForeignKey("devices.id"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    energy_watts = Column(Numeric(10, 2), nullable=False)
    
    # Relationships
    device = relationship("Device", back_populates="telemetry_data")
    
    def __repr__(self):
        return f"<Telemetry(device_id={self.device_id}, timestamp={self.timestamp}, energy_watts={self.energy_watts})>"
    
    @classmethod
    def get_device_telemetry(cls, db, device_id: str, hours: int = 24, limit: int = 1000):
        """Get telemetry data for a specific device within the last N hours."""
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        return db.query(cls).filter(
            cls.device_id == device_id,
            cls.timestamp >= cutoff_time
        ).order_by(cls.timestamp.desc()).limit(limit).all()
    
    @classmethod
    def get_user_devices_summary(cls, db, user_id: str, hours: int = 24):
        """Get energy consumption summary for all user devices."""
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get all telemetry data for user's devices
        query = db.query(cls).join(Device).filter(
            Device.user_id == user_id,
            cls.timestamp >= cutoff_time
        )
        
        telemetry_data = query.all()
        
        if not telemetry_data:
            return {
                "total_energy": 0,
                "average_power": 0,
                "peak_power": 0,
                "device_count": 0,
                "data_points": 0
            }
        
        total_energy = sum(data.energy_watts for data in telemetry_data)
        average_power = total_energy / len(telemetry_data)
        peak_power = max(data.energy_watts for data in telemetry_data)
        
        # Get unique device count
        device_count = len(set(data.device_id for data in telemetry_data))
        
        return {
            "total_energy": round(total_energy, 2),
            "average_power": round(average_power, 2),
            "peak_power": round(peak_power, 2),
            "device_count": device_count,
            "data_points": len(telemetry_data)
        }
    
    @classmethod
    def get_hourly_consumption(cls, db, device_id: str, hours: int = 24):
        """Get hourly energy consumption for a device."""
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Group by hour and calculate average power
        hourly_data = db.query(
            func.date_trunc('hour', cls.timestamp).label('hour'),
            func.avg(cls.energy_watts).label('avg_power'),
            func.max(cls.energy_watts).label('peak_power'),
            func.count(cls.id).label('data_points')
        ).filter(
            cls.device_id == device_id,
            cls.timestamp >= cutoff_time
        ).group_by(
            func.date_trunc('hour', cls.timestamp)
        ).order_by(
            func.date_trunc('hour', cls.timestamp)
        ).all()
        
        return [
            {
                "hour": data.hour.isoformat(),
                "average_power": round(float(data.avg_power), 2),
                "peak_power": round(float(data.peak_power), 2),
                "data_points": data.data_points
            }
            for data in hourly_data
        ]

# Create composite index for better query performance
Index('idx_telemetry_device_timestamp', Telemetry.device_id, Telemetry.timestamp)
Index('idx_telemetry_timestamp_device', Telemetry.timestamp, Telemetry.device_id)
