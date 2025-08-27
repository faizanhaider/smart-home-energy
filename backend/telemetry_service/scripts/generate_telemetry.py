#!/usr/bin/env python3
"""
Smart Home Energy Monitoring - Telemetry Generation Script

This script generates simulated telemetry data for testing the system.
It allows users to input their email, find their devices, and specify time period for telemetry generation.
"""

import requests
import random
import time
import uuid
import psycopg2
from datetime import datetime, timedelta
import json
import getpass

def get_user_devices_by_email(email):
    """Get devices for a specific user by email."""
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
        
        # First get the user by email
        cursor.execute("""
            SELECT id, email 
            FROM users 
            WHERE email = %s AND is_active = true
        """, (email,))
        
        user = cursor.fetchone()
        if not user:
            print(f"❌ No user found with email: {email}")
            cursor.close()
            conn.close()
            return None, []
        
        user_id, user_email = user
        print(f"✅ Found user: ({user_email})")
        
        # Get all active devices for this user
        cursor.execute("""
            SELECT d.id, d.name, d.device_type, d.location, d.manufacturer, d.model
            FROM devices d
            WHERE d.user_id = %s AND d.is_active = true
            ORDER BY d.name
        """, (user_id,))
        
        devices = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return user, devices
    except Exception as e:
        print(f"❌ Database error: {e}")
        return None, []

def get_time_period_input():
    """Get user input for time period."""
    print("\n📅 Select time period for telemetry generation:")
    print("1. Last 24 hours")
    print("2. Last 7 days")
    print("3. Last 30 days")
    print("4. Custom hours")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-4): ").strip()
            
            if choice == "1":
                return 24, "24 hours"
            elif choice == "2":
                return 24 * 7, "7 days"
            elif choice == "3":
                return 24 * 30, "30 days"
            elif choice == "4":
                hours = int(input("Enter number of hours: "))
                if hours > 0 and hours <= 8760:  # Max 1 year
                    return hours, f"{hours} hours"
                else:
                    print("❌ Please enter a valid number of hours (1-8760)")
            else:
                print("❌ Please enter a valid choice (1-4)")
        except ValueError:
            print("❌ Please enter a valid number")
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            exit(0)

def get_data_interval_input():
    """Get user input for data interval."""
    print("\n⏱️  Select data interval:")
    print("1. Every minute (high detail)")
    print("2. Every 5 minutes (medium detail)")
    print("3. Every 15 minutes (low detail)")
    print("4. Every hour (summary)")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-4): ").strip()
            
            if choice == "1":
                return 1, "every minute"
            elif choice == "2":
                return 5, "every 5 minutes"
            elif choice == "3":
                return 15, "every 15 minutes"
            elif choice == "4":
                return 60, "every hour"
            else:
                print("❌ Please enter a valid choice (1-4)")
        except ValueError:
            print("❌ Please enter a valid number")
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            exit(0)

def generate_telemetry(user, devices, hours, interval_minutes):
    """Generate and send telemetry data to the telemetry service."""
    
    # Configuration
    TELEMETRY_API_URL = "http://localhost:8001"
    
    print(f"\n🚀 Starting telemetry generation...")
    print(f"👤 User: {user[1]}")
    print(f"📱 Devices: {len(devices)}")
    print(f"📡 API Endpoint: {TELEMETRY_API_URL}")
    print(f"⏰ Duration: {hours} hours")
    print(f"📊 Interval: {interval_minutes} minutes")
    
    # Calculate total data points
    total_minutes = hours * 60
    data_points = total_minutes // interval_minutes
    print(f"📈 Total data points to generate: {data_points}")
    
    # Display devices
    print(f"\n📱 Devices found:")
    for i, device in enumerate(devices, 1):
        device_id, name, device_type, location, manufacturer, model = device
        print(f"  {i}. {name} ({device_type})")
        if location:
            print(f"     📍 Location: {location}")
        if manufacturer and model:
            print(f"     🏭 {manufacturer} {model}")
        print(f"     🆔 ID: {device_id}")
    
    # Energy consumption ranges for different device types (in watts)
    device_energy_ranges = {
        'refrigerator': (80, 150),      # Fridge: 80-150W
        'air_conditioner': (1000, 3500), # AC: 1000-3500W
        'light': (5, 100),              # Light: 5-100W
        'computer': (50, 300),          # Computer: 50-300W
        'garage_door': (200, 500),      # Garage door: 200-500W
        'appliance': (500, 2000),       # General appliances: 500-2000W
        'tv': (50, 400),                # TV: 50-400W
        'washing_machine': (300, 2000), # Washing machine: 300-2000W
        'dishwasher': (1200, 2400),     # Dishwasher: 1200-2400W
        'microwave': (600, 1200),       # Microwave: 600-1200W
        'oven': (1000, 5000),           # Oven: 1000-5000W
        'heater': (1000, 3000),         # Heater: 1000-3000W
        'fan': (20, 100),               # Fan: 20-100W
        'pump': (100, 500),             # Pump: 100-500W
        'sensor': (1, 10)               # Sensor: 1-10W
    }
    
    # Ask for confirmation
    print(f"\n⚠️  This will generate {data_points * len(devices)} total telemetry records")
    confirm = input("Continue? (y/N): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("❌ Operation cancelled")
        return
    
    successful_requests = 0
    failed_requests = 0
    
    # Set start time to beginning of the specified period
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    print(f"\n⏳ Generating telemetry data...")
    print(f"🕐 Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"🕐 End time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    # Generate data for each interval
    for interval in range(data_points):
        timestamp = start_time + timedelta(minutes=interval * interval_minutes)
        ts = timestamp.isoformat() + "Z"
        
        for device_id, device_name, device_type, location, manufacturer, model in devices:
            # Simulate realistic energy patterns
            hour = timestamp.hour
            minute = timestamp.minute
            
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
            
            # Add minute-based variations for some devices
            if device_type in ['light', 'tv', 'computer']:
                if minute % 15 == 0:  # Every 15 minutes
                    energy_multiplier *= random.uniform(0.5, 1.5)  # More variation
            
            energy_watts = min_watts + (max_watts - min_watts) * random.random()
            energy_watts *= energy_multiplier
            
            payload = {
                "device_id": str(device_id),
                "timestamp": ts,
                "energy_watts": round(energy_watts, 2)
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
        if interval % 10 == 0 or interval == data_points - 1:
            progress = (interval + 1) / data_points * 100
            print(f"⏳ Progress: {progress:.1f}% ({interval + 1}/{data_points})")
    
    print(f"\n✅ Telemetry generation complete!")
    print(f"📊 Successful requests: {successful_requests}")
    print(f"❌ Failed requests: {failed_requests}")
    print(f"📈 Total data points: {successful_requests + failed_requests}")
    print(f"📱 Devices processed: {len(devices)}")
    print(f"⏰ Time period: {hours} hours")
    print(f"📊 Data interval: {interval_minutes} minutes")

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

def main():
    """Main function to run the telemetry generator."""
    print("🏠 Smart Home Energy Monitoring - Telemetry Generator")
    print("=" * 60)
    
    # Test connection first
    if not test_connection():
        print("\n🔧 Troubleshooting:")
        print("1. Ensure Docker is running")
        print("2. Start services: docker-compose up -d")
        print("3. Wait for all services to be ready")
        print("4. Run this script again")
        return
    
    print("\n👤 User Authentication")
    print("-" * 30)
    
    # Get user email
    while True:
        email = input("Enter your email address: ").strip()
        if email and '@' in email:
            break
        print("❌ Please enter a valid email address")
    
    # Find user and devices
    user, devices = get_user_devices_by_email(email)
    if not user or not devices:
        print("❌ No devices found for this user")
        return
    
    # Get time period
    hours, time_description = get_time_period_input()
    
    # Get data interval
    interval_minutes, interval_description = get_data_interval_input()
    
    # Summary
    print(f"\n📋 Generation Summary:")
    print(f"👤 User: {user[1]}")
    print(f"📱 Devices: {len(devices)}")
    print(f"⏰ Time period: {time_description}")
    print(f"📊 Data interval: {interval_description}")
    print(f"📈 Total data points: {(hours * 60 // interval_minutes) * len(devices)}")
    
    # Generate telemetry
    generate_telemetry(user, devices, hours, interval_minutes)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please check your configuration and try again.")
