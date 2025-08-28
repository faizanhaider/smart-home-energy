#!/usr/bin/env python3
"""
Smart Home Energy Monitoring - Add Sample Devices Script

This script adds sample devices for a user to test the telemetry service integration.
"""

import psycopg2
import uuid
from datetime import datetime, timezone

def add_sample_devices():
    """Add sample devices for testing."""
    
    # Database connection parameters
    DB_CONFIG = {
        'host': 'localhost',
        'port': 5432,
        'database': 'smart_home_energy',
        'user': 'smart_home_user',
        'password': 'smart_home_password'
    }
    
    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("✅ Connected to database successfully")
        
        # Get the first user (you can modify this to get a specific user)
        cursor.execute("SELECT id, email FROM users where email = 'admin@smarthome.com' LIMIT 1")
        user = cursor.fetchone()
        
        if not user:
            print("❌ No users found in database")
            return
        
        user_id, user_email = user
        print(f"📱 Adding devices for user: {user_email} (ID: {user_id})")
        
        # Sample devices to add
        sample_devices = [
            {
                'name': 'Kitchen Fridge',
                'device_type': 'refrigerator',
                'location': 'Kitchen'
            },
            {
                'name': 'Living Room AC',
                'device_type': 'air_conditioner',
                'location': 'Living Room'
            },
            {
                'name': 'Bedroom Light',
                'device_type': 'light',
                'location': 'Bedroom'
            },
            {
                'name': 'Office Computer',
                'device_type': 'computer',
                'location': 'Home Office'
            },
            {
                'name': 'Garage Door',
                'device_type': 'garage_door',
                'location': 'Garage'
            },
            {
                'name': 'Dishwasher',
                'device_type': 'appliance',
                'location': 'Kitchen'
            },
            {
                'name': 'Washing Machine',
                'device_type': 'appliance',
                'location': 'Laundry Room'
            },
            {
                'name': 'Microwave',
                'device_type': 'appliance',
                'location': 'Kitchen'
            }
        ]
        
        # Check if devices already exist for this user
        cursor.execute("SELECT COUNT(*) FROM devices WHERE user_id = %s", (user_id,))
        existing_count = cursor.fetchone()[0]
        
        if existing_count > 0:
            print(f"⚠️  User already has {existing_count} devices")
            response = input("Do you want to add more devices? (y/n): ")
            if response.lower() != 'y':
                print("Skipping device creation")
                return
        
        # Add devices
        added_count = 0
        for device in sample_devices:
            device_id = str(uuid.uuid4())
            
            cursor.execute("""
                INSERT INTO devices (id, user_id, name, device_type, location, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                device_id,
                user_id,
                device['name'],
                device['device_type'],
                device['location'],
                True,
                datetime.now(timezone.utc),
                datetime.now(timezone.utc)
            ))
            
            if cursor.rowcount > 0:
                added_count += 1
                print(f"✅ Added device: {device['name']}")
            else:
                print(f"⚠️  Device already exists: {device['name']}")
        
        # Commit changes
        conn.commit()
        print(f"\n🎉 Successfully added {added_count} new devices")
        
        # Show all devices for the user
        cursor.execute("""
            SELECT name, device_type, location, is_active, created_at 
            FROM devices 
            WHERE user_id = %s 
            ORDER BY created_at
        """, (user_id,))
        
        devices = cursor.fetchall()
        print(f"\n📱 Total devices for user: {len(devices)}")
        for device in devices:
            name, device_type, location, is_active, created_at = device
            status = "🟢 Active" if is_active else "🔴 Inactive"
            print(f"  • {name} ({device_type}) - {location} - {status}")
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'conn' in locals():
            cursor.close()
            conn.close()
            print("🔌 Database connection closed")

if __name__ == "__main__":
    print("🏠 Smart Home Energy Monitoring - Add Sample Devices")
    print("=" * 60)
    
    add_sample_devices()
