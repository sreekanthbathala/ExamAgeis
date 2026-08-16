import cv2
import numpy as np
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Try importing mediapipe
try:
    import mediapipe as mp
    MP_AVAILABLE = True
except ImportError:
    MP_AVAILABLE = False
    logger.warning("Mediapipe is not installed or import failed. Face detection will fall back.")

# Try importing dlib
try:
    import dlib
    DLIB_AVAILABLE = True
except ImportError:
    DLIB_AVAILABLE = False
    logger.warning("Dlib is not installed or import failed. Dlib fallback will be unavailable.")

class FaceDetector:
    def __init__(self, dlib_predictor_path: str = None):
        self.mp_face_mesh = None
        self.dlib_detector = None
        self.dlib_predictor = None
        
        # Initialize primary detector (Mediapipe Face Mesh)
        if MP_AVAILABLE and hasattr(mp, 'solutions'):
            try:
                self.mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
                    static_image_mode=False,
                    max_num_faces=4, # Detect multiple faces to count violations
                    refine_landmarks=True, # Improves iris landmarks accuracy for eye gaze
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
                logger.info("Mediapipe Face Mesh initialized successfully.")
            except Exception as e:
                logger.error(f"Error initializing Mediapipe Face Mesh: {e}")
                self.mp_face_mesh = None
        else:
            logger.info("Mediapipe solutions module is not available on this platform/Python version. Will use fallbacks.")

        # Initialize fallback detector (Dlib)
        if not self.mp_face_mesh and DLIB_AVAILABLE:
            try:
                self.dlib_detector = dlib.get_frontal_face_detector()
                if dlib_predictor_path:
                    import os
                    if os.path.exists(dlib_predictor_path):
                        self.dlib_predictor = dlib.shape_predictor(dlib_predictor_path)
                        logger.info("Dlib Frontal Face Detector and shape predictor initialized.")
                    else:
                        logger.warning(f"Dlib shape predictor path not found: {dlib_predictor_path}")
            except Exception as e:
                logger.error(f"Error initializing Dlib: {e}")

    def detect_faces(self, frame: np.ndarray):
        """
        Detects faces in a frame and returns:
        - face_count (int): Number of faces detected.
        - face_landmarks_list: List of landmarks (Mediapipe NormalizedLandmarks list or Dlib points).
        """
        if frame is None:
            return 0, []

        # Convert to RGB as required by Mediapipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 1. Primary: Mediapipe
        if self.mp_face_mesh:
            try:
                results = self.mp_face_mesh.process(rgb_frame)
                if results.multi_face_landmarks:
                    face_count = len(results.multi_face_landmarks)
                    return face_count, results.multi_face_landmarks
                return 0, []
            except Exception as e:
                logger.error(f"Mediapipe detection error: {e}")

        # 2. Fallback: Dlib
        if self.dlib_detector:
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.dlib_detector(gray)
                face_count = len(faces)
                
                landmarks_list = []
                if self.dlib_predictor:
                    for face in faces:
                        shape = self.dlib_predictor(gray, face)
                        landmarks_list.append(shape)
                return face_count, landmarks_list
            except Exception as e:
                logger.error(f"Dlib detection error: {e}")

        # 3. Last Fallback: Mock / Log error
        logger.error("No facial detection libraries are available or initialized.")
        return 0, []
