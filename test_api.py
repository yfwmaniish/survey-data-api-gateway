#!/usr/bin/env python3
"""
Simple test script for the API Gateway without requiring database or Redis
"""

import httpx
import asyncio
import json
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"
DEMO_API_KEY = "demo-key-123"
ADMIN_API_KEY = "admin-key-456"

async def test_api_endpoints():
    """Test various API endpoints"""
    
    async with httpx.AsyncClient() as client:
        print("🚀 Testing Survey Data API Gateway")
        print("=" * 50)
        
        # Test 1: Root endpoint
        print("\n1. Testing root endpoint...")
        try:
            response = await client.get(f"{BASE_URL}/")
            print(f"✅ Root endpoint: {response.status_code}")
            print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"❌ Root endpoint failed: {str(e)}")
        
        # Test 2: Health check
        print("\n2. Testing health check...")
        try:
            response = await client.get(f"{BASE_URL}/health")
            print(f"✅ Health check: {response.status_code}")
            health_data = response.json()
            print(f"   Status: {health_data.get('status')}")
            print(f"   Services: {health_data.get('services')}")
        except Exception as e:
            print(f"❌ Health check failed: {str(e)}")
        
        # Test 3: Authentication test
        print("\n3. Testing authentication...")
        try:
            headers = {"Authorization": f"Bearer {DEMO_API_KEY}"}
            response = await client.get(f"{BASE_URL}/user/info", headers=headers)
            print(f"✅ Auth test: {response.status_code}")
            if response.status_code == 200:
                user_info = response.json()
                print(f"   User: {user_info.get('user_id')}")
                print(f"   Permissions: {user_info.get('permissions')}")
        except Exception as e:
            print(f"❌ Auth test failed: {str(e)}")
        
        # Test 4: Export formats
        print("\n4. Testing export formats...")
        try:
            headers = {"Authorization": f"Bearer {DEMO_API_KEY}"}
            response = await client.get(f"{BASE_URL}/export/formats", headers=headers)
            print(f"✅ Export formats: {response.status_code}")
            if response.status_code == 200:
                formats = response.json()
                print(f"   Supported formats: {list(formats.get('supported_formats', {}).keys())}")
        except Exception as e:
            print(f"❌ Export formats failed: {str(e)}")
        
        # Test 5: WebSocket connections info
        print("\n5. Testing WebSocket connections...")
        try:
            response = await client.get(f"{BASE_URL}/ws/connections")
            print(f"✅ WebSocket info: {response.status_code}")
            if response.status_code == 200:
                ws_info = response.json()
                print(f"   Active connections: {ws_info.get('total_connections', 0)}")
        except Exception as e:
            print(f"❌ WebSocket info failed: {str(e)}")
        
        # Test 6: Query templates
        print("\n6. Testing query templates...")
        try:
            headers = {"Authorization": f"Bearer {DEMO_API_KEY}"}
            response = await client.get(f"{BASE_URL}/query/templates", headers=headers)
            print(f"✅ Query templates: {response.status_code}")
            if response.status_code == 200:
                templates = response.json()
                print(f"   Available templates: {len(templates)}")
        except Exception as e:
            print(f"❌ Query templates failed: {str(e)}")
        
        # Test 7: Admin dashboard (should work even without DB)
        print("\n7. Testing admin dashboard...")
        try:
            headers = {"Authorization": f"Bearer {ADMIN_API_KEY}"}
            response = await client.get(f"{BASE_URL}/admin/dashboard", headers=headers)
            print(f"✅ Admin dashboard: {response.status_code}")
            if response.status_code == 200:
                dashboard = response.json()
                print(f"   System status: {dashboard.get('system_status')}")
        except Exception as e:
            print(f"❌ Admin dashboard failed: {str(e)}")
        
        # Test 8: Performance monitoring
        print("\n8. Testing performance monitoring...")
        try:
            headers = {"Authorization": f"Bearer {ADMIN_API_KEY}"}
            response = await client.get(f"{BASE_URL}/admin/performance/detailed", headers=headers)
            print(f"✅ Performance monitoring: {response.status_code}")
        except Exception as e:
            print(f"❌ Performance monitoring failed: {str(e)}")
        
        # Test 9: JWT Token creation
        print("\n9. Testing JWT token creation...")
        try:
            response = await client.post(
                f"{BASE_URL}/auth/token",
                params={"user_id": "test_user", "permissions": ["read", "query"]}
            )
            print(f"✅ JWT creation: {response.status_code}")
            if response.status_code == 200:
                token_data = response.json()
                print(f"   Token type: {token_data.get('token_type')}")
                print(f"   Expires in: {token_data.get('expires_in')} seconds")
        except Exception as e:
            print(f"❌ JWT creation failed: {str(e)}")
        
        print("\n" + "=" * 50)
        print("🎉 API Gateway testing completed!")
        print("\nNote: Database-dependent features will show errors until PostgreSQL is configured.")
        print("Redis-dependent features (caching, rate limiting) are using in-memory fallbacks.")

if __name__ == "__main__":
    print("Starting API Gateway tests...")
    print("Make sure the server is running: uvicorn app.main:app --reload")
    print()
    
    try:
        asyncio.run(test_api_endpoints())
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
