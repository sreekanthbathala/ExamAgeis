import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session
from app.models.database import get_db
from app.models.student import Student
from app.schemas.auth_schema import StudentLoginRequest, AdminLoginRequest, TokenResponse
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/admin-login", auto_error=False)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generates a secure JWT token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    """
    Decodes and validates a JWT token.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.PyJWTError as e:
        logger.error(f"JWT Verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Student:
    """
    Dependency to fetch the currently authenticated user from the token.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token"
        )
    payload = verify_token(token)
    roll_number = payload.get("sub")
    if not roll_number:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalid: missing subject"
        )
    user = db.query(Student).filter(Student.roll_number == roll_number).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.post("/student-login", response_model=TokenResponse)
def student_login(request: StudentLoginRequest, db: Session = Depends(get_db)):
    """
    Authenticates a student. If the student roll number does not exist,
    they are automatically registered in the database dynamically (convenient demo mode).
    """
    try:
        # Search for student by roll number
        student = db.query(Student).filter(Student.roll_number == request.roll_number).first()
        
        if not student:
            # Register new student dynamically
            logger.info(f"Student {request.name} ({request.roll_number}) not found. Registering dynamically.")
            student = Student(
                name=request.name,
                roll_number=request.roll_number,
                email=request.email
            )
            db.add(student)
            db.commit()
            db.refresh(student)
        
        # Issue JWT token
        token_data = {"sub": student.roll_number, "role": "student", "name": student.name}
        access_token = create_access_token(token_data)
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            roll_number=student.roll_number,
            name=student.name,
            role="student"
        )
    except Exception as e:
        logger.error(f"Error in student-login: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/admin-login", response_model=TokenResponse)
def admin_login(request: AdminLoginRequest, db: Session = Depends(get_db)):
    """
    Authenticates an administrator using credentials stored in the DB.
    """
    # Look up the admin user
    admin = db.query(Student).filter(Student.roll_number == "ADMIN").first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="System Administrator not configured."
        )

    # Verify password
    # Admin username is flexible (can be 'admin' or matching the database record)
    if request.username.lower() != "admin":
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    pw_bytes = request.password.encode('utf-8')
    hashed_bytes = admin.hashed_password.encode('utf-8') if admin.hashed_password else b""
    
    if not admin.hashed_password or not bcrypt.checkpw(pw_bytes, hashed_bytes):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    # Issue JWT token
    token_data = {"sub": admin.roll_number, "role": "admin", "name": admin.name}
    access_token = create_access_token(token_data)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        roll_number=admin.roll_number,
        name=admin.name,
        role="admin"
    )
