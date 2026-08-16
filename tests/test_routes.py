import os
import pytest
import bcrypt
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from app.main import app
from app.models.database import get_db
from app.models.student import Student

DB_FILE = "test_exam_aegis.db"
DB_URL = f"sqlite:///{DB_FILE}"

# Use a temporary file-based SQLite database
test_engine = create_engine(
    DB_URL, 
    connect_args={"check_same_thread": False}
)

def override_get_db():
    with Session(test_engine) as session:
        yield session

# Override the get_db dependency in the FastAPI application
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(name="client", scope="module")
def client_fixture():
    # Cleanup any leftovers
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    # Import models to register on SQLModel metadata
    from app.models.student import Student
    from app.models.exam_session import ExamSession
    from app.models.violation_log import ViolationLog
    
    # Create all tables in the test database
    SQLModel.metadata.create_all(test_engine)
    
    # Seed the admin user into the test database
    with Session(test_engine) as session:
        hashed = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode('utf-8')
        admin_user = Student(
            name="System Administrator",
            roll_number="ADMIN",
            email="admin@examaegis.com",
            hashed_password=hashed
        )
        session.add(admin_user)
        session.commit()
        
    with TestClient(app) as c:
        yield c

    # Teardown: Remove the test database file
    if os.path.exists(DB_FILE):
        try:
            os.remove(DB_FILE)
        except Exception:
            pass

def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_student_login_and_exam_flow(client):
    # 1. Login student (should dynamically register since roll CS-999 doesn't exist)
    payload = {
        "name": "Test Student",
        "roll_number": "CS-999",
        "email": "test@student.com",
        "exam_id": "TEST101"
    }
    response = client.post("/api/auth/student-login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "student"
    assert data["name"] == "Test Student"
    assert "access_token" in data
    
    token = data["access_token"]
    headers = {"Authorization": f"Bearer ${token}"}  # Correct Bearer format (fastapi security matches Bearer <token>)
    
    # Let's override headers to use exact Bearer token value
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Start exam session
    session_payload = {"exam_id": "TEST101"}
    exam_response = client.post("/api/exam/start", json=session_payload, headers=headers)
    assert exam_response.status_code == 200
    exam_data = exam_response.json()
    assert exam_data["status"] == "active"
    assert exam_data["exam_id"] == "TEST101"
    
    session_id = exam_data["id"]
    
    # 3. Check status of session
    status_response = client.get(f"/api/exam/status/{session_id}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "active"
    
    # 4. End exam session
    end_response = client.post(f"/api/exam/end/{session_id}", headers=headers)
    assert end_response.status_code == 200
    assert end_response.json()["status"] == "completed"

def test_admin_login(client):
    # Try invalid password
    invalid_payload = {
        "username": "admin",
        "password": "wrongpassword"
    }
    response = client.post("/api/auth/admin-login", json=invalid_payload)
    assert response.status_code == 401
    
    # Correct password
    valid_payload = {
        "username": "admin",
        "password": "admin123"
    }
    response = client.post("/api/auth/admin-login", json=valid_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "admin"
    assert "access_token" in data

def test_websocket_client_events(client):
    # Establish a student session first
    payload = {
        "name": "Socket Student",
        "roll_number": "CS-SOCKET",
        "email": "socket@student.com",
        "exam_id": "TEST202"
    }
    response = client.post("/api/auth/student-login", json=payload)
    token = response.json()["access_token"]
    
    session_response = client.post("/api/exam/start", json={"exam_id": "TEST202"}, headers={"Authorization": f"Bearer {token}"})
    session_id = session_response.json()["id"]
    
    # Connect to WebSocket
    with client.websocket_connect(f"/api/monitor/ws/{session_id}?token={token}") as websocket:
        # Send tab_switch client event
        websocket.send_json({
            "type": "client_event",
            "event": "tab_switch",
            "timestamp": "2026-08-16T20:17:00.000Z"
        })
        
        # We expect to receive a response detailing the alert
        response_data = websocket.receive_json()
        assert response_data["type"] == "proctor_result"
        alerts = response_data["alerts"]
        assert len(alerts) == 1
        assert alerts[0]["violation_type"] == "tab_switch"
        assert alerts[0]["severity"] == "medium"

    # End session
    client.post(f"/api/exam/end/{session_id}", headers={"Authorization": f"Bearer {token}"})

def test_integrity_score_endpoint(client):
    # Establish student and login
    payload = {
        "name": "Score Student",
        "roll_number": "CS-SCORE",
        "email": "score@student.com",
        "exam_id": "TEST303"
    }
    response = client.post("/api/auth/student-login", json=payload)
    token = response.json()["access_token"]
    
    session_response = client.post("/api/exam/start", json={"exam_id": "TEST303"}, headers={"Authorization": f"Bearer {token}"})
    session_id = session_response.json()["id"]

    # Trigger a couple of tab switches over the socket to generate violations
    with client.websocket_connect(f"/api/monitor/ws/{session_id}?token={token}") as websocket:
        websocket.send_json({
            "type": "client_event",
            "event": "tab_switch",
            "timestamp": "2026-08-16T20:17:00Z"
        })
        websocket.receive_json() # Wait for response

    # Query the integrity score endpoint
    score_response = client.get(f"/api/report/integrity-score/{session_id}", headers={"Authorization": f"Bearer {token}"})
    assert score_response.status_code == 200
    score_data = score_response.json()
    assert score_data["exam_session_id"] == session_id
    # We had 1 medium violation (tab_switch), which subtracts 3 points. Total should be 97!
    assert score_data["score"] == 97
    assert score_data["breakdown"]["medium"] == 1

    # End session
    client.post(f"/api/exam/end/{session_id}", headers={"Authorization": f"Bearer {token}"})
