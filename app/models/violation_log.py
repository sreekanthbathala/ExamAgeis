from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class ViolationLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    exam_session_id: int = Field(foreign_key="examsession.id")
    violation_type: str  # no_face, multiple_faces, gaze_away, phone_detected, book_detected, voice_detected, mouth_open
    severity: str        # low, medium, high
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: str        # JSON details as a string for extensibility
    screenshot_path: Optional[str] = Field(default=None, nullable=True)
