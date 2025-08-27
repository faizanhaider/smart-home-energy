"""
Device model for managing smart home devices.
"""

from sqlalchemy import Column, String, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel


class Device(BaseModel):
    """Device model for smart home energy monitoring."""
    
    __tablename__ = "devices"
    
    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    device_type = Column(String(100), index=True)
    location = Column(String(255))
    is_active = Column(Boolean, default=True)
    manufacturer = Column(String(255))
    model = Column(String(255))
    serial_number = Column(String(255))
    power_rating_watts = Column(String(50))  # e.g., "100-500W"
    description = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="devices")
    telemetry_data = relationship("Telemetry", back_populates="device", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Device(id={self.id}, name={self.name}, type={self.device_type})>"
    
    @property
    def current_status(self) -> str:
        """Get current device status."""
        if not self.is_active:
            return "inactive"
        return "active"
    
    def get_energy_consumption_summary(self, db, hours: int = 24):
        """Get energy consumption summary for the last N hours."""
        from .telemetry import Telemetry
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get telemetry data for the last N hours
        recent_data = db.query(Telemetry).filter(
            Telemetry.device_id == self.id,
            Telemetry.timestamp >= cutoff_time
        ).all()
        
        if not recent_data:
            return {
                "total_energy": 0,
                "average_power": 0,
                "peak_power": 0,
                "data_points": 0
            }
        
        total_energy = sum(data.energy_watts for data in recent_data)
        average_power = total_energy / len(recent_data)
        peak_power = max(data.energy_watts for data in recent_data)
        
        return {
            "total_energy": round(total_energy, 2),
            "average_power": round(average_power, 2),
            "peak_power": round(peak_power, 2),
            "data_points": len(recent_data)
        }
