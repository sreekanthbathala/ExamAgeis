from sqlmodel import Session
from app.models.violation_log import ViolationLog
from app.config import settings

def calculate_integrity_score(exam_session_id: int, db: Session) -> dict:
    """
    Queries all ViolationLog entries for a session and computes a weighted integrity score.
    Low severity = -1, Medium severity = -3, High severity = -7.
    Score is floored at 0.
    """
    violations = db.query(ViolationLog).filter(
        ViolationLog.exam_session_id == exam_session_id
    ).all()

    counts = {}
    breakdown = {"low": 0, "medium": 0, "high": 0}

    for v in violations:
        # Count by type
        counts[v.violation_type] = counts.get(v.violation_type, 0) + 1
        # Count by severity
        sev = v.severity.lower()
        if sev in breakdown:
            breakdown[sev] += 1

    # Subtract weighted scores
    deductions = (
        breakdown["low"] * settings.VIOLATION_WEIGHT_LOW +
        breakdown["medium"] * settings.VIOLATION_WEIGHT_MEDIUM +
        breakdown["high"] * settings.VIOLATION_WEIGHT_HIGH
    )

    score = max(0, 100 - deductions)

    return {
        "exam_session_id": exam_session_id,
        "score": score,
        "counts": counts,
        "breakdown": breakdown
    }
