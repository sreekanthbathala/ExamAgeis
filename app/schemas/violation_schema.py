from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ViolationLogResponse(BaseModel):
    id: int
    exam_session_id: int
    violation_type: str
    severity: str
    timestamp: datetime
    details: str

    model_config = {
        "from_attributes": True
    }

class ViolationSummary(BaseModel):
    violation_type: str
    count: int
