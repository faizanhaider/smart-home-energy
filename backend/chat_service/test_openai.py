#!/usr/bin/env python3
"""
Test script for OpenAI integration in Chat Service.
Run this script to test the OpenAI endpoints.
"""

import asyncio
import httpx
import json
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8002"
OPENAI_ENDPOINTS = [
    "/openai/status",
    "/openai/sample-queries",
    "/intents"
]

async def test_endpoint(client: httpx.AsyncClient, endpoint: str, method: str = "GET", data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Test a specific endpoint."""
    try:
        if method == "GET":
            response = await client.get(f"{BASE_URL}{endpoint}")
        elif method == "POST":
            response = await client.post(f"{BASE_URL}{endpoint}", json=data)
        else:
            return {"error": f"Unsupported method: {method}"}
        
        if response.status_code == 200:
            return {
                "endpoint": endpoint,
                "status": "success",
                "status_code": response.status_code,
                "data": response.json()
            }
        else:
            return {
                "endpoint": endpoint,
                "status": "error",
                "status_code": response.status_code,
                "error": response.text
            }
    except Exception as e:
        return {
            "endpoint": endpoint,
            "status": "exception",
            "error": str(e)
        }

async def test_openai_integration():
    """Test OpenAI integration endpoints."""
    print("🧪 Testing OpenAI Integration in Chat Service")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        # Test basic endpoints
        for endpoint in OPENAI_ENDPOINTS:
            result = await test_endpoint(client, endpoint)
            print(f"\n📡 {endpoint}")
            print(f"   Status: {result['status']}")
            if result['status'] == 'success':
                print(f"   Response: {json.dumps(result['data'], indent=2)}")
            else:
                print(f"   Error: {result.get('error', 'Unknown error')}")
        
        # Test OpenAI status specifically
        print("\n🔍 Testing OpenAI Status:")
        status_result = await test_endpoint(client, "/openai/status")
        if status_result['status'] == 'success':
            status_data = status_result['data']
            print(f"   OpenAI Status: {status_data.get('status', 'unknown')}")
            print(f"   Message: {status_data.get('message', 'No message')}")
            if status_data.get('status') == 'connected':
                print(f"   Model: {status_data.get('model', 'Unknown')}")
                print(f"   Test Response: {status_data.get('test_response', 'None')}")
        else:
            print(f"   Failed to get status: {status_result.get('error', 'Unknown error')}")
        
        # Test sample queries
        print("\n📝 Testing Sample Queries:")
        queries_result = await test_endpoint(client, "/openai/sample-queries")
        if queries_result['status'] == 'success':
            queries_data = queries_result['data']
            print(f"   Available queries: {len(queries_data.get('sample_queries', []))}")
            for i, query in enumerate(queries_data.get('sample_queries', [])[:3]):
                print(f"   {i+1}. {query}")
            print("   ... (showing first 3 queries)")
        else:
            print(f"   Failed to get sample queries: {queries_result.get('error', 'Unknown error')}")
        
        # Test intents endpoint
        print("\n🎯 Testing Supported Intents:")
        intents_result = await test_endpoint(client, "/intents")
        if intents_result['status'] == 'success':
            intents_data = intents_result['data']
            print(f"   OpenAI Integration: {intents_data.get('features', {}).get('openai_integration', False)}")
            print(f"   Available Intents: {len(intents_data.get('intents', {}))}")
            print(f"   AI Capabilities: {len(intents_data.get('ai_capabilities', []))}")
        else:
            print(f"   Failed to get intents: {intents_result.get('error', 'Unknown error')}")

def main():
    """Main function."""
    try:
        asyncio.run(test_openai_integration())
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")

if __name__ == "__main__":
    main()
