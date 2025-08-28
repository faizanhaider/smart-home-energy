#!/usr/bin/env python3
"""
Test script to verify authentication integration across all services.
"""

import asyncio
import httpx
import json
from typing import Dict, Any

# Configuration
AUTH_SERVICE_URL = "http://localhost:8000"
CHAT_SERVICE_URL = "http://localhost:8001"
TELEMETRY_SERVICE_URL = "http://localhost:8002"
WEBSOCKET_SERVICE_URL = "http://localhost:8003"

async def test_auth_service():
    """Test the auth service endpoints."""
    print("🔐 Testing Auth Service...")
    
    async with httpx.AsyncClient() as client:
        # Test health check
        response = await client.get(f"{AUTH_SERVICE_URL}/health")
        print(f"  Health check: {response.status_code}")
        
        # Test registration
        user_data = {
            "email": "test@example.com",
            "password": "testpassword123",
            "first_name": "Test",
            "last_name": "User"
        }
        
        response = await client.post(f"{AUTH_SERVICE_URL}/register", json=user_data)
        print(f"  Registration: {response.status_code}")
        
        if response.status_code == 201:
            user = response.json()
            print(f"  User created: {user['email']}")
            
            # Test login
            login_data = {
                "email": "test@example.com",
                "password": "testpassword123"
            }
            
            response = await client.post(f"{AUTH_SERVICE_URL}/login", json=login_data)
            print(f"  Login: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                token = token_data["access_token"]
                print(f"  Token received: {token[:20]}...")
                
                # Test token verification
                headers = {"Authorization": f"Bearer {token}"}
                response = await client.post(f"{AUTH_SERVICE_URL}/verify-token", headers=headers)
                print(f"  Token verification: {response.status_code}")
                
                if response.status_code == 200:
                    user_info = response.json()
                    print(f"  User verified: {user_info['email']}")
                    return token, user_info
                else:
                    print(f"  Token verification failed: {response.text}")
            else:
                print(f"  Login failed: {response.text}")
        else:
            print(f"  Registration failed: {response.text}")
    
    return None, None

async def test_chat_service(token: str):
    """Test the chat service with authentication."""
    print("\n💬 Testing Chat Service...")
    
    if not token:
        print("  Skipping - no token available")
        return
    
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test chat query
        chat_data = {
            "question": "How much energy did my devices use today?"
        }
        
        response = await client.post(f"{CHAT_SERVICE_URL}/query", json=chat_data, headers=headers)
        print(f"  Chat query: {response.status_code}")
        
        if response.status_code == 200:
            chat_response = response.json()
            print(f"  Response: {chat_response['summary'][:50]}...")
        else:
            print(f"  Chat query failed: {response.text}")
        
        # Test chat history
        response = await client.get(f"{CHAT_SERVICE_URL}/history", headers=headers)
        print(f"  Chat history: {response.status_code}")
        
        if response.status_code == 200:
            history = response.json()
            print(f"  History count: {len(history)}")
        else:
            print(f"  History failed: {response.text}")

async def test_telemetry_service(token: str):
    """Test the telemetry service with authentication."""
    print("\n📊 Testing Telemetry Service...")
    
    if not token:
        print("  Skipping - no token available")
        return
    
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test user devices summary
        response = await client.get(f"{TELEMETRY_SERVICE_URL}/user/devices", headers=headers)
        print(f"  User devices: {response.status_code}")
        
        if response.status_code == 200:
            devices = response.json()
            print(f"  Devices count: {len(devices)}")
        else:
            print(f"  User devices failed: {response.text}")
        
        # Test user summary
        response = await client.get(f"{TELEMETRY_SERVICE_URL}/user/summary", headers=headers)
        print(f"  User summary: {response.status_code}")
        
        if response.status_code == 200:
            summary = response.json()
            print(f"  Total energy: {summary['total_energy']}W")
        else:
            print(f"  User summary failed: {response.text}")

async def test_websocket_service(token: str):
    """Test the WebSocket service with authentication."""
    print("\n🔌 Testing WebSocket Service...")
    
    if not token:
        print("  Skipping - no token available")
        return
    
    # Test health check
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{WEBSOCKET_SERVICE_URL}/health")
        print(f"  Health check: {response.status_code}")
        
        if response.status_code == 200:
            health = response.json()
            print(f"  Service status: {health['status']}")
        else:
            print(f"  Health check failed: {response.text}")

async def test_unauthenticated_access():
    """Test that unauthenticated access is properly rejected."""
    print("\n🚫 Testing Unauthenticated Access...")
    
    async with httpx.AsyncClient() as client:
        # Test chat service without token
        chat_data = {"question": "Test question"}
        response = await client.post(f"{CHAT_SERVICE_URL}/query", json=chat_data)
        print(f"  Chat without auth: {response.status_code} (should be 401)")
        
        # Test telemetry service without token
        response = await client.get(f"{TELEMETRY_SERVICE_URL}/user/devices")
        print(f"  Telemetry without auth: {response.status_code} (should be 401)")

async def main():
    """Run all authentication tests."""
    print("🧪 Starting Authentication Integration Tests\n")
    
    try:
        # Test auth service
        token, user_info = await test_auth_service()
        
        # Test other services with authentication
        await test_chat_service(token)
        await test_telemetry_service(token)
        await test_websocket_service(token)
        
        # Test unauthenticated access
        await test_unauthenticated_access()
        
        print("\n✅ Authentication integration tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
