"""
CareBase — Automated Tests
Run with: python -m pytest test_app.py -v
"""

import pytest
from app import app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ---------------------------------------------------------------------------
# Test 1: Health check endpoint
# ---------------------------------------------------------------------------
def test_health_endpoint(client):
    """GET /health should return 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# Test 2: Get all doctors
# ---------------------------------------------------------------------------
def test_get_doctors(client):
    """GET /api/doctors should return a list of doctors."""
    response = client.get("/api/doctors")
    assert response.status_code == 200
    data = response.get_json()
    assert "doctors" in data
    assert len(data["doctors"]) >= 1
    assert "name" in data["doctors"][0]
    assert "specialty" in data["doctors"][0]


# ---------------------------------------------------------------------------
# Test 3: Create an appointment (valid data)
# ---------------------------------------------------------------------------
def test_create_appointment(client):
    """POST /api/appointments with valid JSON and auth should return 201."""
    # Register and login first
    client.post("/api/auth/register", json={
        "username": "testuser", "password": "password", 
        "email": "test@test.com", "full_name": "Test Patient"
    })
    
    payload = {
        "doctor_id": 1,
        "date": "2026-06-15",
        "time": "10:00 AM",
        "symptoms": "chest pain and shortness of breath",
    }
    response = client.post("/api/appointments", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["appointment"]["patient_name"] == "Test Patient"
    assert data["appointment"]["doctor_id"] == 1
    assert "ai_analysis" in data["appointment"]

# ---------------------------------------------------------------------------
# Test 3.5: Double booking prevention
# ---------------------------------------------------------------------------
def test_double_booking(client):
    """Trying to book the same slot twice should return 409."""
    client.post("/api/auth/register", json={
        "username": "testuser2", "password": "password", 
        "email": "test2@test.com", "full_name": "Test Patient"
    })
    payload = {
        "doctor_id": 1,
        "date": "2026-06-15",
        "time": "10:00 AM",
        "symptoms": "chest pain",
    }
    response = client.post("/api/appointments", json=payload)
    assert response.status_code == 409
    data = response.get_json()
    assert "already booked" in data["error"]


# ---------------------------------------------------------------------------
# Test 4: Create appointment with missing fields returns 400
# ---------------------------------------------------------------------------
def test_create_appointment_missing_fields(client):
    """POST /api/appointments with missing fields should return 400."""
    client.post("/api/auth/register", json={
        "username": "testuser3", "password": "password", 
        "email": "test3@test.com", "full_name": "Test Patient"
    })
    payload = {"doctor_id": 1}
    response = client.post("/api/appointments", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


# ---------------------------------------------------------------------------
# Test 5: Get appointments list
# ---------------------------------------------------------------------------
def test_get_appointments(client):
    """GET /api/appointments should return a list."""
    response = client.get("/api/appointments")
    assert response.status_code == 200
    data = response.get_json()
    assert "appointments" in data
    assert isinstance(data["appointments"], list)


# ---------------------------------------------------------------------------
# Test 6: Get non-existent appointment returns 404
# ---------------------------------------------------------------------------
def test_get_appointment_not_found(client):
    """GET /api/appointments/9999 should return 404."""
    response = client.get("/api/appointments/9999")
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data


# ---------------------------------------------------------------------------
# Test 7: AI symptom analysis endpoint
# ---------------------------------------------------------------------------
def test_analyze_symptoms(client):
    """POST /api/analyze should return specialty and precautions."""
    payload = {"symptoms": "I have a severe headache and dizziness"}
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert "specialty" in data
    assert "predicted_conditions" in data
    assert "precautions" in data
    assert "recommended_doctor" in data
