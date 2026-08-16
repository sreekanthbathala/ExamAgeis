import pytest
import bcrypt
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from app.main import app
from app.models.database import get_db
from app.models.student import Student

# Use an isolated, in-memory SQLite database for testing
test_engine = create_engine(
    "sqlite:///:memory:", 
    connect_args={"check_same_thread": False}
)

def override_get_db():
    with Session(test_engine) as session:
        yield session

# Override the get_db dependency in the FastAPI application
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(name="client", scope="module")
def client_fixture():
    # Create tables in the isolated test database
    from app.models.student import Student
    from app.models.exam_session import ExamSession
    from app.models.violation_log import ViolationLog
    
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
