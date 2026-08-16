import numpy as np
import cv2
from app.utils.logger import get_logger

logger = get_logger(__name__)

def estimate_gaze_ratio(face_landmarks, frame, is_dlib=False) -> float:
    """
    Estimates the horizontal gaze ratio (0.0 to 1.0).
    A value around 0.5 indicates looking straight ahead.
    Values deviating significantly (e.g., < 0.35 or > 0.65) indicate looking left or right.
    """
    if not face_landmarks:
        return 0.5

    if not is_dlib:
        # Mediapipe Face Mesh landmarks
        # Left eye: 33 (left corner), 133 (right corner), 468 (iris center)
        # Right eye: 362 (left corner), 263 (right corner), 473 (iris center)
        try:
            # Check if iris landmarks are available
            if len(face_landmarks.landmark) <= 473:
                return 0.5 # Landmarks incomplete for iris refinement
                
            left_corner_l = face_landmarks.landmark[33]
            right_corner_l = face_landmarks.landmark[133]
            pupil_l = face_landmarks.landmark[468]

            left_corner_r = face_landmarks.landmark[362]
            right_corner_r = face_landmarks.landmark[263]
            pupil_r = face_landmarks.landmark[473]

            # Calculate horizontal ratios
            # Ratio = (PupilX - LeftCornerX) / (RightCornerX - LeftCornerX)
            # Left Eye:
            denom_l = right_corner_l.x - left_corner_l.x
            ratio_l = (pupil_l.x - left_corner_l.x) / denom_l if denom_l != 0 else 0.5

            # Right Eye:
            denom_r = right_corner_r.x - left_corner_r.x
            ratio_r = (pupil_r.x - left_corner_r.x) / denom_r if denom_r != 0 else 0.5

            # Average ratio
            return (ratio_l + ratio_r) / 2.0
        except Exception as e:
            logger.error(f"Error in Mediapipe gaze estimation: {e}")
            return 0.5

    else:
        # Dlib landmarks shape predictor (shape has 68 points)
        # Left eye: 36 to 41. Right eye: 42 to 47.
        try:
            # Helper to get pupil ratio via thresholding within eye coordinates
            def get_eye_pupil_ratio(eye_points, shape, gray_frame):
                # Get coordinates of eye boundaries
                x_coords = [shape.part(p).x for p in eye_points]
                y_coords = [shape.part(p).y for p in eye_points]
                min_x, max_x = min(x_coords), max(x_coords)
                min_y, max_y = min(y_coords), max(y_coords)
                
                # Check for tiny boundary to prevent empty slice
                if max_x <= min_x or max_y <= min_y:
                    return 0.5

                # Crop eye region
                eye_region = gray_frame[min_y:max_y, min_x:max_x]
                if eye_region.size == 0:
                    return 0.5

                # Threshold to isolate the dark pupil
                _, threshold_eye = cv2.threshold(eye_region, 50, 255, cv2.THRESH_BINARY_INV)
                
                # Find centroid of dark region
                moments = cv2.moments(threshold_eye)
                if moments['m00'] != 0:
                    cx = int(moments['m10'] / moments['m00'])
                    # Normalize pupil position within cropped eye width
                    ratio = cx / (max_x - min_x)
                    return ratio
                return 0.5

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Left Eye landmarks: 36, 37, 38, 39, 40, 41
            ratio_l = get_eye_pupil_ratio(range(36, 42), face_landmarks, gray)
            # Right Eye landmarks: 42, 43, 44, 45, 46, 47
            ratio_r = get_eye_pupil_ratio(range(42, 48), face_landmarks, gray)
            
            return (ratio_l + ratio_r) / 2.0
        except Exception as e:
            logger.error(f"Error in Dlib gaze estimation: {e}")
            return 0.5
            
def is_looking_away(gaze_ratio: float, min_thresh: float = 0.35, max_thresh: float = 0.65) -> bool:
    """
    Checks if gaze ratio is outside acceptable straight-looking range.
    """
    return gaze_ratio < min_thresh or gaze_ratio > max_thresh
