"""
Tests for authentication endpoints
"""
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_register_new_user():
    """Test user registration"""
    response = client.post(
        "/api/auth/register",
        json={"username": "testuser", "password": "testpass123"}
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_register_duplicate_user():
    """Test registering duplicate username"""
    # Register first user
    client.post(
        "/api/auth/register",
        json={"username": "duplicate", "password": "testpass123"}
    )
    
    # Try to register same username again
    response = client.post(
        "/api/auth/register",
        json={"username": "duplicate", "password": "testpass123"}
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_login_success():
    """Test successful login"""
    # Register user
    client.post(
        "/api/auth/register",
        json={"username": "logintest", "password": "testpass123"}
    )
    
    # Login
    response = client.post(
        "/api/auth/login",
        json={"username": "logintest", "password": "testpass123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password():
    """Test login with wrong password"""
    # Register user
    client.post(
        "/api/auth/register",
        json={"username": "wrongpass", "password": "testpass123"}
    )
    
    # Try to login with wrong password
    response = client.post(
        "/api/auth/login",
        json={"username": "wrongpass", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]


def test_login_nonexistent_user():
    """Test login with non-existent user"""
    response = client.post(
        "/api/auth/login",
        json={"username": "nonexistent", "password": "testpass123"}
    )
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]


def test_get_current_user():
    """Test getting current user info"""
    # Register and login
    response = client.post(
        "/api/auth/register",
        json={"username": "currentuser", "password": "testpass123"}
    )
    token = response.json()["access_token"]
    
    # Get current user
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "currentuser"
    assert "id" in data


def test_protected_endpoint_without_token():
    """Test accessing protected endpoint without token"""
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_protected_endpoint_with_invalid_token():
    """Test accessing protected endpoint with invalid token"""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
