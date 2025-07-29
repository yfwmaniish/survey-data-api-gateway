import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_endpoint():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Survey Data API Gateway"
    assert "version" in data
    assert "status" in data

def test_health_endpoint():
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code in [200, 503]  # Could be unhealthy if no DB
    data = response.json()
    assert "status" in data
    assert "services" in data

def test_auth_required():
    """Test that authentication is required for protected endpoints"""
    # Test without authentication
    response = client.post("/query/", json={"sql": "SELECT 1"})
    assert response.status_code == 403

def test_query_with_demo_key():
    """Test query endpoint with demo API key"""
    headers = {"Authorization": "Bearer demo-key-123"}
    
    # Test simple query (will fail without database, but should pass auth)
    response = client.post("/query/", 
                          json={"sql": "SELECT 1 as test"}, 
                          headers=headers)
    
    # Should pass auth but may fail on DB connection
    assert response.status_code != 403  # Not auth error

def test_invalid_sql():
    """Test that invalid SQL is rejected"""
    headers = {"Authorization": "Bearer demo-key-123"}
    
    # Test dangerous SQL
    response = client.post("/query/", 
                          json={"sql": "DROP TABLE users"}, 
                          headers=headers)
    assert response.status_code == 400

def test_get_datasets():
    """Test datasets endpoint"""
    headers = {"Authorization": "Bearer demo-key-123"}
    response = client.get("/datasets", headers=headers)
    
    # Should pass auth (may fail on DB connection)
    assert response.status_code != 403

def test_user_info():
    """Test user info endpoint"""
    headers = {"Authorization": "Bearer demo-key-123"}
    response = client.get("/user/info", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["user_id"] == "demo_user"
    assert "permissions" in data
    assert "read" in data["permissions"]
