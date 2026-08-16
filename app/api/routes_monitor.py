import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlmodel import Session
from app.models.database import get_db
from app.models.exam_session import ExamSession
from app.config import settings
from app.utils.frame_utils import base64_to_cv2
from app.utils.logger import get_logger

# Import CV modules
from app.core.face_detection import FaceDetector
from app.core.eye_gaze import estimate_gaze_ratio
from app.core.blink_detection import get_average_ear
from app.core.head_pose import estimate_head_pose
from app.core.mouth_tracking import calculate_mar
from app.core.object_detection import ObjectDetector
from app.core.audio_detection import analyze_audio_chunk
from app.core.violation_engine import process_violations

logger = get_logger(__name__)
router = APIRouter(prefix="/monitor", tags=["Real-time Proctoring"])

# Initialize singletons for ML models to avoid reload overhead per connection
face_detector = FaceDetector(settings.DLIB_PREDICTOR_PATH)
object_detector = ObjectDetector(settings.YOLO_MODEL_PATH)

@router.websocket("/ws/{session_id}")
async def monitor_websocket(
    websocket: WebSocket,
    session_id: int,
    token: str = Query(None),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for streaming webcam frames and audio chunks.
    Processes frames through detection modules in sequence and streams back violation alerts.
    """
    # Accept connection
    await websocket.accept()
    logger.info(f"WebSocket connection request accepted for Session: {session_id}")

    # Validate exam session exists and is active
    session_record = db.get(ExamSession, session_id)
    if not session_record:
        logger.warning(f"Rejecting WS connection: session {session_id} not found.")
        await websocket.send_json({"type": "error", "message": "Session not found."})
        await websocket.close()
        return

    if session_record.status != "active":
        logger.warning(f"Rejecting WS connection: session {session_id} is already {session_record.status}.")
        await websocket.send_json({"type": "error", "message": f"Session status is {session_record.status}."})
        await websocket.close()
        return

    # Connection-specific state cache for audio integration
    audio_state = {
        "voice_spotted": False,
        "max_rms": 0.0
    }

    is_dlib_mode = (face_detector.mp_face_mesh is None) and (face_detector.dlib_detector is not None)

    try:
        while True:
            # Wait for message from client (can be TEXT or BYTES)
            message = await websocket.receive()

            # 1. Handle TEXT messages (expecting base64 webcam frames in JSON)
            if "text" in message:
                try:
                    payload = json.loads(message["text"])
                    msg_type = payload.get("type")
                    
                    if msg_type == "frame":
                        b64_data = payload.get("data")
                        if not b64_data:
                            continue
                            
                        # Convert to OpenCV frame
                        frame = base64_to_cv2(b64_data)
                        if frame is None:
                            logger.warning(f"[Session {session_id}] Received corrupted frame.")
                            continue
                            
                        height, width, _ = frame.shape
                        
                        # --- SEQUENCE OF DETECTION MODULES ---
                        
                        # a. Face Detection
                        face_count, landmarks_list = face_detector.detect_faces(frame)
                        
                        # Initialize signal values
                        gaze_ratio = 0.5
                        ear = 0.3
                        head_angles = (0.0, 0.0, 0.0)
                        mar = 0.0
                        
                        if face_count > 0:
                            # Use primary face landmarks
                            face_landmarks = landmarks_list[0]
                            
                            # b. Eye Gaze Estimation
                            gaze_ratio = estimate_gaze_ratio(face_landmarks, frame, is_dlib=is_dlib_mode)
                            
                            # c. Blink Detection
                            ear = get_average_ear(face_landmarks, is_dlib=is_dlib_mode)
                            
                            # d. Head Pose Estimation
                            head_angles = estimate_head_pose(face_landmarks, width, height, is_dlib=is_dlib_mode)
                            
                            # e. Mouth Tracking
                            mar = calculate_mar(face_landmarks, is_dlib=is_dlib_mode)

                        # f. Object Detection (YOLOv8)
                        detections, person_count = object_detector.detect_objects(frame)
                        
                        # If YOLO detects multiple people, reconcile face count
                        if person_count > face_count:
                            face_count = person_count

                        # Pull accumulated audio signals
                        audio_voice_detected = audio_state["voice_spotted"]
                        audio_rms = audio_state["max_rms"]
                        
                        # --- VIOLATION ENGINE ---
                        alerts = process_violations(
                            db=db,
                            exam_session_id=session_id,
                            face_count=face_count,
                            gaze_ratio=gaze_ratio,
                            ear=ear,
                            head_angles=head_angles,
                            mar=mar,
                            detections=detections,
                            audio_voice_detected=audio_voice_detected,
                            audio_rms=audio_rms
                        )
                        
                        # Reset audio indicators for the next time-frame window
                        audio_state["voice_spotted"] = False
                        audio_state["max_rms"] = 0.0
                        
                        # Send alerts back to client in real-time
                        await websocket.send_json({
                            "type": "proctor_result",
                            "alerts": alerts,
                            "metrics": {
                                "face_count": face_count,
                                "gaze_ratio": round(gaze_ratio, 3),
                                "ear": round(ear, 3),
                                "head_pose": {
                                    "yaw": round(head_angles[0], 1),
                                    "pitch": round(head_angles[1], 1)
                                },
                                "mar": round(mar, 3),
                                "objects_detected": [d["label"] for d in detections if d["label"] != "person"]
                            }
                        })
                        
                    elif msg_type == "ping":
                        await websocket.send_json({"type": "pong"})
                        
                except Exception as ex:
                    logger.error(f"Error parsing websocket text message: {ex}")
            
            # 2. Handle BINARY messages (expecting browser audio chunks)
            elif "bytes" in message:
                audio_bytes = message["bytes"]
                
                try:
                    # Run chunk through audio detector
                    voice_detected, rms_value, desc = analyze_audio_chunk(
                        audio_bytes, 
                        threshold=settings.AUDIO_RMS_THRESHOLD
                    )
                    
                    if voice_detected:
                        audio_state["voice_spotted"] = True
                        audio_state["max_rms"] = max(audio_state["max_rms"], rms_value)
                        logger.debug(f"[Session {session_id}] Voice activity flagged in stream: {desc}")
                        
                except Exception as ex:
                    logger.error(f"Error processing audio bytes: {ex}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket exception for session {session_id}: {e}")
    finally:
        # Avoid leaving connection dangling
        try:
            await websocket.close()
        except Exception:
            pass
