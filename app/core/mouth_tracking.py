from app.core.blink_detection import calculate_distance
from app.utils.logger import get_logger

logger = get_logger(__name__)

def calculate_mar(face_landmarks, is_dlib=False) -> float:
    """
    Calculates the Mouth Aspect Ratio (MAR) to detect mouth opening (possible talking).
    MAR = |Vertical inner mouth height| / |Horizontal mouth width|
    """
    if not face_landmarks:
        return 0.0

    if not is_dlib:
        # Mediapipe Face Mesh landmarks
        # Inner mouth:
        # Top lip center: 13, Bottom lip center: 14
        # Left corner: 78, Right corner: 308
        try:
            landmarks = face_landmarks.landmark
            vertical_dist = calculate_distance(landmarks[13], landmarks[14])
            horizontal_dist = calculate_distance(landmarks[78], landmarks[308])
            
            if horizontal_dist == 0:
                return 0.0
            return vertical_dist / horizontal_dist
        except Exception as e:
            logger.error(f"Error calculating Mediapipe MAR: {e}")
            return 0.0
    else:
        # Dlib 68-point landmarks
        # Inner mouth points:
        # Left corner: 60, Right corner: 64
        # Top lip center: 62, Bottom lip center: 66
        try:
            def dlib_pt(part):
                return (part.x, part.y)

            vertical_dist = calculate_distance(
                dlib_pt(face_landmarks.part(62)), dlib_pt(face_landmarks.part(66))
            )
            horizontal_dist = calculate_distance(
                dlib_pt(face_landmarks.part(60)), dlib_pt(face_landmarks.part(64))
            )
            
            if horizontal_dist == 0:
                return 0.0
            return vertical_dist / horizontal_dist
        except Exception as e:
            logger.error(f"Error calculating Dlib MAR: {e}")
            return 0.0

def is_mouth_open(mar: float, threshold: float = 0.50) -> bool:
    """
    Checks if MAR is above the mouth-open threshold.
    """
    return mar > threshold
