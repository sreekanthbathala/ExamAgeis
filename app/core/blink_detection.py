import numpy as np
from app.utils.logger import get_logger

logger = get_logger(__name__)

def calculate_distance(p1, p2):
    """
    Calculates Euclidean distance between two points.
    Supports either object with x, y fields (Mediapipe NormalizedLandmark)
    or indexable point (Dlib/numpy).
    """
    if hasattr(p1, 'x') and hasattr(p1, 'y'):
        return np.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (getattr(p1, 'z', 0) - getattr(p2, 'z', 0))**2)
    else:
        return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def calculate_ear(eye_landmarks) -> float:
    """
    Calculates Eye Aspect Ratio (EAR) given 6 landmarks:
    p1: outer corner, p4: inner corner
    p2, p6: top/bottom pair 1
    p3, p5: top/bottom pair 2
    EAR = (|p2 - p6| + |p3 - p5|) / (2 * |p1 - p4|)
    """
    p1, p2, p3, p4, p5, p6 = eye_landmarks
    d_v1 = calculate_distance(p2, p6)
    d_v2 = calculate_distance(p3, p5)
    d_h = calculate_distance(p1, p4)
    
    if d_h == 0:
        return 0.0
    return (d_v1 + d_v2) / (2.0 * d_h)

def get_average_ear(face_landmarks, is_dlib=False) -> float:
    """
    Computes average EAR across left and right eyes.
    """
    if not face_landmarks:
        return 0.30 # Default open eyes value

    if not is_dlib:
        # Mediapipe landmarks map
        # Left eye: p1=33, p2=160, p3=158, p4=133, p5=153, p6=144
        # Right eye: p1=362, p2=385, p3=387, p4=263, p5=373, p6=380
        try:
            landmarks = face_landmarks.landmark
            left_eye = [
                landmarks[33], landmarks[160], landmarks[158],
                landmarks[133], landmarks[153], landmarks[144]
            ]
            right_eye = [
                landmarks[362], landmarks[385], landmarks[387],
                landmarks[263], landmarks[373], landmarks[380]
            ]
            ear_l = calculate_ear(left_eye)
            ear_r = calculate_ear(right_eye)
            return (ear_l + ear_r) / 2.0
        except Exception as e:
            logger.error(f"Error computing Mediapipe EAR: {e}")
            return 0.30
    else:
        # Dlib landmarks map
        # Left eye points: 36, 37, 38, 39, 40, 41
        # Right eye points: 42, 43, 44, 45, 46, 47
        try:
            def dlib_pt(part):
                return (part.x, part.y)

            left_eye = [
                dlib_pt(face_landmarks.part(36)), dlib_pt(face_landmarks.part(37)),
                dlib_pt(face_landmarks.part(38)), dlib_pt(face_landmarks.part(39)),
                dlib_pt(face_landmarks.part(40)), dlib_pt(face_landmarks.part(41))
            ]
            right_eye = [
                dlib_pt(face_landmarks.part(42)), dlib_pt(face_landmarks.part(43)),
                dlib_pt(face_landmarks.part(44)), dlib_pt(face_landmarks.part(45)),
                dlib_pt(face_landmarks.part(46)), dlib_pt(face_landmarks.part(47))
            ]
            ear_l = calculate_ear(left_eye)
            ear_r = calculate_ear(right_eye)
            return (ear_l + ear_r) / 2.0
        except Exception as e:
            logger.error(f"Error computing Dlib EAR: {e}")
            return 0.30

def is_blinking(ear: float, threshold: float = 0.20) -> bool:
    """
    Checks if current EAR is below the closure threshold.
    """
    return ear < threshold
