import time
import json
from datetime import datetime
from sqlmodel import Session
from app.models.violation_log import ViolationLog
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# In-memory store for session temporal state and cooldowns
# Structure: { session_id: { "last_seen_face": float, "last_logged": { violation_type: float } } }
session_states = {}

def get_or_create_state(session_id: int):
    now = time.time()
    if session_id not in session_states:
        session_states[session_id] = {
            "first_frame_time": now,
            "last_seen_face": now,
            "last_time_gaze_ok": now,
            "last_time_head_pose_ok": now,
            "blink_closed_start_time": now,
            "last_time_mouth_closed": now,
            "last_time_audio_quiet": now,
            "last_logged": {} # violation_type -> timestamp
        }
    return session_states[session_id]

def process_violations(
    db: Session,
    exam_session_id: int,
    face_count: int,
    gaze_ratio: float,
    ear: float,
    head_angles: tuple[float, float, float],
    mar: float,
    detections: list[dict],
    audio_voice_detected: bool,
    audio_rms: float
) -> list[dict]:
    """
    Applies configurable thresholds and temporal aggregation to determine violations.
    Logs violations to the database if thresholds are crossed and cooldown permits.
    Returns a list of alerts to send to the frontend.
    """
    now = time.time()
    state = get_or_create_state(exam_session_id)
    alerts = []
    
    # Helper to check if a violation is in cooldown (e.g., 10 seconds)
    def can_log_violation(v_type: str, cooldown: float = 10.0) -> bool:
        last_logged = state["last_logged"].get(v_type, 0)
        return (now - last_logged) > cooldown

    # Helper to log violation and update state
    def record_violation(v_type: str, severity: str, details_dict: dict):
        if can_log_violation(v_type):
            try:
                log = ViolationLog(
                    exam_session_id=exam_session_id,
                    violation_type=v_type,
                    severity=severity,
                    timestamp=datetime.utcnow(),
                    details=json.dumps(details_dict)
                )
                db.add(log)
                db.commit()
                state["last_logged"][v_type] = now
                logger.info(f"[Session {exam_session_id}] Logged violation: {v_type} ({severity})")
            except Exception as e:
                logger.error(f"Error logging violation to DB: {e}")
        
        # Add to immediate response alerts
        alerts.append({
            "violation_type": v_type,
            "severity": severity,
            "message": details_dict.get("message", "Violation detected")
        })

    # --- 1. Face Count Analysis ---
    if face_count == 0:
        missing_dur = now - state["last_seen_face"]
        # Trigger alert immediately if missing, and log to DB after 5 seconds threshold
        if missing_dur > 5.0:
            record_violation("no_face", "high", {
                "duration": missing_dur,
                "message": "No face detected in webcam view for more than 5 seconds!"
            })
        else:
            alerts.append({
                "violation_type": "no_face_warning",
                "severity": "low",
                "message": "Please face the camera. No face detected."
            })
    else:
        state["last_seen_face"] = now

    if face_count > 1:
        record_violation("multiple_faces", "high", {
            "face_count": face_count,
            "message": "Multiple faces detected in the webcam view!"
        })

    # Only run facial detail checks if exactly 1 face is visible
    if face_count == 1:
        # --- 2. Gaze Direction check ---
        # settings values
        gaze_min = settings.EYE_GAZE_MIN
        gaze_max = settings.EYE_GAZE_MAX
        if gaze_ratio < gaze_min or gaze_ratio > gaze_max:
            gaze_away_dur = now - state["last_time_gaze_ok"]
            if gaze_away_dur > 3.0:
                record_violation("gaze_away", "medium", {
                    "gaze_ratio": gaze_ratio,
                    "duration": gaze_away_dur,
                    "message": "Looking away from the screen detected (Gaze)."
                })
        else:
            state["last_time_gaze_ok"] = now

        # --- 3. Head Pose check ---
        yaw, pitch, roll = head_angles
        yaw_th = settings.HEAD_POSE_YAW_THRESHOLD
        pitch_th = settings.HEAD_POSE_PITCH_THRESHOLD
        if abs(yaw) > yaw_th or abs(pitch) > pitch_th:
            pose_away_dur = now - state["last_time_head_pose_ok"]
            if pose_away_dur > 3.0:
                record_violation("head_turned", "medium", {
                    "yaw": yaw,
                    "pitch": pitch,
                    "duration": pose_away_dur,
                    "message": f"Looking away detected (Head turned: Yaw={yaw:.1f}°, Pitch={pitch:.1f}°)"
                })
        else:
            state["last_time_head_pose_ok"] = now

        # --- 4. Blink / Sleeping check ---
        ear_th = settings.BLINK_EAR_THRESHOLD
        if ear < ear_th:
            closed_dur = now - state["blink_closed_start_time"]
            if closed_dur > settings.BLINK_DURATION_THRESHOLD_SEC:
                record_violation("eyes_closed", "medium", {
                    "ear": ear,
                    "duration": closed_dur,
                    "message": "Eyes closed or sleeping detected."
                })
        else:
            state["blink_closed_start_time"] = now

        # --- 5. Mouth open (talking) check ---
        mar_th = settings.MOUTH_MAR_THRESHOLD
        if mar > mar_th:
            mouth_dur = now - state["last_time_mouth_closed"]
            if mouth_dur > 3.0:
                record_violation("talking_detected", "medium", {
                    "mar": mar,
                    "duration": mouth_dur,
                    "message": "Talking detected (mouth open for sustained duration)."
                })
        else:
            state["last_time_mouth_closed"] = now

    # --- 6. Object Detection Analysis ---
    for det in detections:
        label = det["label"]
        conf = det["confidence"]
        
        if label == "cell phone":
            record_violation("phone_detected", "high", {
                "confidence": conf,
                "message": f"Unauthorized device detected: Cell Phone ({conf * 100:.1f}%)"
            })
        elif label == "book":
            record_violation("book_detected", "medium", {
                "confidence": conf,
                "message": f"Unauthorized item detected: Book ({conf * 100:.1f}%)"
            })
        elif label == "laptop":
            # Sometimes student laptops are visible. Log as low severity.
            record_violation("laptop_detected", "low", {
                "confidence": conf,
                "message": f"Secondary screen detected: Laptop ({conf * 100:.1f}%)"
            })

    # --- 7. Audio Signal Analysis ---
    if audio_voice_detected:
        audio_dur = now - state["last_time_audio_quiet"]
        if audio_dur > 3.0:
            record_violation("voice_detected", "medium", {
                "rms": audio_rms,
                "duration": audio_dur,
                "message": f"Voice or loud background noise detected (RMS: {audio_rms:.4f})"
            })
    else:
        state["last_time_audio_quiet"] = now

    return alerts

def clean_session_state(session_id: int):
    """
    Cleans state memory when exam ends.
    """
    if session_id in session_states:
        del session_states[session_id]
        logger.info(f"Cleaned proctoring state for session {session_id}")
