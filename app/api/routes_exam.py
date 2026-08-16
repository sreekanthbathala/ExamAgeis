from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from app.models.database import get_db
from app.models.exam_session import ExamSession
from app.api.routes_auth import get_current_user
from app.models.student import Student
from app.schemas.exam_schema import ExamSessionStartRequest, ExamSessionResponse
from app.core.violation_engine import clean_session_state
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/exam", tags=["Exam Management"])

@router.post("/start", response_model=ExamSessionResponse)
def start_exam_session(
    request: ExamSessionStartRequest, 
    db: Session = Depends(get_db), 
    current_user: Student = Depends(get_current_user)
):
    """
    Starts a new exam session for the authenticated student.
    """
    try:
        # Check if the student already has an active session
        active_session = db.query(ExamSession).filter(
            ExamSession.student_id == current_user.id,
            ExamSession.status == "active"
        ).first()

        if active_session:
            logger.info(f"Student {current_user.name} already has an active session: {active_session.id}")
            return active_session

        # Create new exam session
        new_session = ExamSession(
            student_id=current_user.id,
            exam_id=request.exam_id,
            start_time=datetime.utcnow(),
            status="active"
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        
        logger.info(f"Started exam session {new_session.id} for student {current_user.name}")
        return new_session
    except Exception as e:
        logger.error(f"Error starting exam session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error starting exam")

@router.post("/end/{session_id}", response_model=ExamSessionResponse)
def end_exam_session(
    session_id: int, 
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    """
    Marks an exam session as completed. Cleans up cached proctoring state.
    """
    try:
        session = db.get(ExamSession, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Exam session not found")
        
        # Verify that this session belongs to the current user (unless admin)
        if session.student_id != current_user.id and current_user.roll_number != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Not authorized to modify this session"
            )

        if session.status == "completed":
            return session

        # Update status
        session.status = "completed"
        session.end_time = datetime.utcnow()
        db.add(session)
        db.commit()
        db.refresh(session)

        # Clear active temporal checks state in the engine
        clean_session_state(session_id)
        logger.info(f"Ended exam session {session_id} for student {current_user.name}")
        return session
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error ending exam session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error ending exam")

@router.get("/status/{session_id}", response_model=ExamSessionResponse)
def get_exam_status(session_id: int, db: Session = Depends(get_db)):
    """
    Retrieves the status of a specific exam session.
    """
    session = db.get(ExamSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Exam session not found")
    return session
