import json
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlmodel import Session
from sqlalchemy import func
from app.models.database import get_db
from app.models.exam_session import ExamSession
from app.models.student import Student
from app.models.violation_log import ViolationLog
from app.api.routes_auth import get_current_user
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/report", tags=["Reporting & Logs"])

@router.get("/sessions")
def get_all_sessions(
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    """
    Returns all exam sessions with student details for the admin panel.
    Requires Admin privileges.
    """
    if current_user.roll_number != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Administrator privileges required."
        )

    try:
        results = db.query(ExamSession, Student).join(
            Student, ExamSession.student_id == Student.id
        ).order_by(ExamSession.start_time.desc()).all()

        sessions_list = []
        for session, student in results:
            sessions_list.append({
                "session_id": session.id,
                "student_id": student.id,
                "student_name": student.name,
                "student_roll": student.roll_number,
                "student_email": student.email,
                "exam_id": session.exam_id,
                "start_time": session.start_time,
                "end_time": session.end_time,
                "status": session.status
            })

        return sessions_list
    except Exception as e:
        logger.error(f"Error querying sessions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error fetching sessions")

@router.get("/violations/{session_id}")
def get_session_violations(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    """
    Retrieves all logged violations for a specific exam session.
    """
    # Verify authorization
    session_rec = db.get(ExamSession, session_id)
    if not session_rec:
        raise HTTPException(status_code=404, detail="Session not found")

    if session_rec.student_id != current_user.id and current_user.roll_number != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not authorized to view these logs."
        )

    try:
        violations = db.query(ViolationLog).filter(
            ViolationLog.exam_session_id == session_id
        ).order_by(ViolationLog.timestamp.asc()).all()

        formatted_violations = []
        for v in violations:
            formatted_violations.append({
                "id": v.id,
                "exam_session_id": v.exam_session_id,
                "violation_type": v.violation_type,
                "severity": v.severity,
                "timestamp": v.timestamp,
                "details": json.loads(v.details) if v.details else {}
            })

        return formatted_violations
    except Exception as e:
        logger.error(f"Error querying violations for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error fetching logs")

@router.get("/summary/{session_id}")
def get_session_summary(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    """
    Returns violation counts grouped by violation type for a session.
    Used for rendering statistics on the dashboard.
    """
    session_rec = db.get(ExamSession, session_id)
    if not session_rec:
        raise HTTPException(status_code=404, detail="Session not found")

    if session_rec.student_id != current_user.id and current_user.roll_number != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )

    try:
        # Group and count by violation_type
        counts = db.query(
            ViolationLog.violation_type,
            func.count(ViolationLog.id).label("count")
        ).filter(
            ViolationLog.exam_session_id == session_id
        ).group_by(ViolationLog.violation_type).all()

        return {c[0]: c[1] for c in counts}
    except Exception as e:
        logger.error(f"Error querying summary: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/export/{session_id}")
def export_violation_log(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    """
    Exports the complete violation log of a session as a downloadable JSON file.
    """
    session_rec = db.get(ExamSession, session_id)
    if not session_rec:
        raise HTTPException(status_code=404, detail="Session not found")

    if current_user.roll_number != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin privileges required."
        )

    try:
        violations = db.query(ViolationLog).filter(
            ViolationLog.exam_session_id == session_id
        ).order_by(ViolationLog.timestamp.asc()).all()

        student_rec = db.get(Student, session_rec.student_id)

        export_data = {
            "session_id": session_rec.id,
            "exam_id": session_rec.exam_id,
            "student_name": student_rec.name if student_rec else "Unknown",
            "student_roll": student_rec.roll_number if student_rec else "Unknown",
            "start_time": session_rec.start_time.isoformat() if session_rec.start_time else None,
            "end_time": session_rec.end_time.isoformat() if session_rec.end_time else None,
            "status": session_rec.status,
            "export_timestamp": datetime.utcnow().isoformat(),
            "violations": [
                {
                    "id": v.id,
                    "type": v.violation_type,
                    "severity": v.severity,
                    "timestamp": v.timestamp.isoformat(),
                    "details": json.loads(v.details) if v.details else {}
                }
                for v in violations
            ]
        }

        # Convert to JSON string
        json_str = json.dumps(export_data, indent=2)
        
        # Create attachment response
        headers = {
            "Content-Disposition": f"attachment; filename=examaegis_session_{session_id}.json"
        }
        
        return Response(content=json_str, media_type="application/json", headers=headers)
        
    except Exception as e:
        logger.error(f"Error exporting logs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error exporting file")
