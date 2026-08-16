from pydantic import BaseModel, EmailStr
from typing import Optional

class StudentLoginRequest(BaseModel):
    name: str
    roll_number: str
    email: EmailStr
    exam_id: str

class AdminLoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    roll_number: str
    name: str
    role: str  # "student" or "admin"
