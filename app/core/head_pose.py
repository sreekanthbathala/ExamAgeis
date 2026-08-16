import cv2
import numpy as np
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Standard 3D model points of a human face
model_points = np.array([
    (0.0, 0.0, 0.0),             # Nose tip
    (0.0, -330.0, -65.0),        # Chin
    (-225.0, 170.0, -135.0),     # Left eye outer corner
    (225.0, 170.0, -135.0),      # Right eye outer corner
    (-150.0, -150.0, -125.0),    # Left mouth corner
    (150.0, -150.0, -125.0)      # Right mouth corner
], dtype=np.float32)

def estimate_head_pose(face_landmarks, width: int, height: int, is_dlib=False):
    """
    Estimates the head pose (yaw, pitch, roll) in degrees.
    Yaw: rotation around Y-axis (left/right look)
    Pitch: rotation around X-axis (up/down look)
    Roll: rotation around Z-axis (tilt)
    """
    if not face_landmarks or width <= 0 or height <= 0:
        return 0.0, 0.0, 0.0

    try:
        # Extract 2D points from landmarks
        image_points = []
        if not is_dlib:
            # Mediapipe mapping:
            # Nose Tip: 4, Chin: 152, Left Eye Outer: 33, Right Eye Outer: 263, Left Mouth: 61, Right Mouth: 291
            landmarks = face_landmarks.landmark
            indices = [4, 152, 33, 263, 61, 291]
            for idx in indices:
                pt = landmarks[idx]
                image_points.append((pt.x * width, pt.y * height))
        else:
            # Dlib mapping:
            # Nose Tip: 30, Chin: 8, Left Eye Outer: 36, Right Eye Outer: 45, Left Mouth: 48, Right Mouth: 54
            indices = [30, 8, 36, 45, 48, 54]
            for idx in indices:
                pt = face_landmarks.part(idx)
                image_points.append((pt.x, pt.y))
                
        image_points = np.array(image_points, dtype=np.float32)

        # Camera internals (approximated)
        focal_length = width
        center = (width / 2.0, height / 2.0)
        camera_matrix = np.array([
            [focal_length, 0.0, center[0]],
            [0.0, focal_length, center[1]],
            [0.0, 0.0, 1.0]
        ], dtype=np.float32)

        dist_coeffs = np.zeros((4, 1), dtype=np.float32) # Assuming no lens distortion

        # Solve for pose (PnP)
        success, rotation_vector, translation_vector = cv2.solvePnP(
            model_points, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE
        )

        if not success:
            return 0.0, 0.0, 0.0

        # Calculate rotation matrix
        rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
        
        # Combine into projection matrix
        projection_matrix = np.hstack((rotation_matrix, translation_vector))
        
        # Decompose projection matrix to get Euler angles
        _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(projection_matrix)
        
        pitch = float(euler_angles[0][0])
        yaw = float(euler_angles[1][0])
        roll = float(euler_angles[2][0])

        # Adjust angle ranges if necessary
        # decomposeProjectionMatrix returns angles in range [-180, 180]
        return yaw, pitch, roll
    except Exception as e:
        logger.error(f"Error in head pose estimation: {e}")
        return 0.0, 0.0, 0.0

def is_head_turned(yaw: float, pitch: float, yaw_thresh: float = 20.0, pitch_thresh: float = 15.0) -> bool:
    """
    Checks if yaw or pitch values exceed threshold angles, meaning the candidate is looking away.
    """
    return abs(yaw) > yaw_thresh or abs(pitch) > pitch_thresh
