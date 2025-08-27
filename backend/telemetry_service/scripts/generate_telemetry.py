#!/usr/bin/env python3
"""
Smart Home Energy Monitoring - Telemetry Generation Script

This script generates simulated telemetry data for testing the system.
It creates 24 hours of one-minute interval energy consumption data for actual devices in the database.
"""

import requests
import random
import time
import uuid
import psycopg2
from datetime import datetime, timedelta
import json

def get_devices_from_db():
    """Get actual devices from the database."""
    DB_CONFIG = {
        'host': 'localhost',
        'port': 5432,
        'database': 'smart_home_energy',
        'user': 'smart_home_user',
        'password': 'smart_home_password'
    }
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Get all active devices
        cursor.execute("""
            SELECT id, name, device_type 
            FROM devices 
            WHERE is_active = true
        """)
        
        devices = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return devices
    except Exception as e:
        print(f"❌ Database error: {e}")
        return []

def generate_telemetry():
    """Generate and send telemetry data to the telemetry service."""
    
    # Configuration
    TELEMETRY_API_URL = "http://localhost:8001"  # Fixed endpoint
    HOURS = 24
    MINUTES_PER_HOUR = 60
    
    print(f"🚀 Starting telemetry generation...")
    print(f"📡 API Endpoint: {TELEMETRY_API_URL}")
    print(f"⏰ Duration: {HOURS} hours ({HOURS * MINUTES_PER_HOUR} data points)")
    
    # Get actual devices from database
    devices = get_devices_from_db()
    if not devices:
        print("❌ No devices found in database")
        return
    
    print(f"📱 Found {len(devices)} devices in database")
    for device in devices:
        print(f"  • {device[1]} ({device[2]}) - ID: {device[0]}")
    
    # Set start time to beginning of today
    start_of_today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Energy consumption ranges for different device types (in watts)
    device_energy_ranges = {
        'refrigerator': (80, 150),      # Fridge: 80-150W
        'air_conditioner': (1000, 3500), # AC: 1000-3500W
        'light': (5, 100),              # Light: 5-100W
        'computer': (50, 300),          # Computer: 50-300W
        'garage_door': (200, 500),      # Garage door: 200-500W
        'appliance': (500, 2000)        # General appliances: 500-2000W
    }
    
    successful_requests = 0
    failed_requests = 0
    
    # Generate data for each minute
    for minute in range(HOURS * MINUTES_PER_HOUR):
        timestamp = start_of_today + timedelta(minutes=minute)
        ts = timestamp.isoformat() + "Z"
        
        for device_id, device_name, device_type in devices:
            # Simulate realistic energy patterns
            hour = timestamp.hour
            
            # Base energy consumption based on device type
            min_watts, max_watts = device_energy_ranges.get(device_type, (100, 500))
            
            # Add time-based variations
            if 6 <= hour <= 9:  # Morning peak
                energy_multiplier = random.uniform(1.2, 1.5)
            elif 18 <= hour <= 22:  # Evening peak
                energy_multiplier = random.uniform(1.3, 1.6)
            elif 23 <= hour or hour <= 5:  # Night (lower usage)
                energy_multiplier = random.uniform(0.3, 0.7)
            else:  # Daytime
                energy_multiplier = random.uniform(0.8, 1.1)
            
            # Add some randomness
            energy_multiplier *= random.uniform(0.9, 1.1)
            
            energy_watts = min_watts + (max_watts - min_watts) * random.random()
            energy_watts *= energy_multiplier
            
            payload = {
                "device_id": str(device_id),  # Fixed field name
                "timestamp": ts,
                "energy_watts": round(energy_watts, 2)  # Fixed field name
            }
            
            try:
                response = requests.post(TELEMETRY_API_URL, json=payload, timeout=5)
                if response.status_code == 201 or response.status_code == 200:
                    successful_requests += 1
                else:
                    failed_requests += 1
                    print(f"❌ Failed to send data: {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
                failed_requests += 1
                print(f"❌ Request failed: {e}")
            
            # Small delay to avoid overwhelming the service
            time.sleep(0.01)
        
        # Progress indicator
        if minute % 60 == 0:
            print(f"⏳ Generated {minute} minutes of data...")
    
    print(f"\n✅ Telemetry generation complete!")
    print(f"📊 Successful requests: {successful_requests}")
    print(f"❌ Failed requests: {failed_requests}")
    print(f"📈 Total data points: {successful_requests + failed_requests}")

def test_connection():
    """Test if the telemetry service is accessible."""
    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            print("✅ Telemetry service is accessible")
            return True
        else:
            print(f"⚠️  Telemetry service responded with status: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to telemetry service: {e}")
        print("💡 Make sure the service is running with: docker-compose up -d")
        return False

if __name__ == "__main__":
    print("🏠 Smart Home Energy Monitoring - Telemetry Generator")
    print("=" * 60)
    
    if test_connection():
        generate_telemetry()
    else:
        print("\n🔧 Troubleshooting:")
        print("1. Ensure Docker is running")
        print("2. Start services: docker-compose up -d")
        print("3. Wait for all services to be ready")
        print("4. Run this script again")
