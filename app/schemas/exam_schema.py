from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ExamSessionStartRequest(BaseModel):
    exam_id: str

class ExamSessionResponse(BaseModel):
    id: int
    student_id: int
    exam_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str

    model_config = {
        "from_attributes": True
    }
