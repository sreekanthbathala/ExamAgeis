from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class ExamSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="student.id")
    exam_id: str
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = Field(default=None, nullable=True)
    status: str = Field(default="active")  # active, completed
