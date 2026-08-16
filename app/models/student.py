from typing import Optional
from sqlmodel import SQLModel, Field

class Student(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    roll_number: str = Field(unique=True, index=True)
    email: str
    hashed_password: Optional[str] = Field(default=None, nullable=True)
