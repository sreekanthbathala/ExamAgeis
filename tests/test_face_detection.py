import pytest
import numpy as np
from app.core.face_detection import FaceDetector

def test_face_detector_init():
    # Verify we can instantiate without errors
    detector = FaceDetector()
    assert detector is not None

def test_detect_faces_empty_frame():
    detector = FaceDetector()
    # Passing None should return 0 faces and empty list
    face_count, landmarks = detector.detect_faces(None)
    assert face_count == 0
    assert len(landmarks) == 0

def test_detect_faces_black_image():
    detector = FaceDetector()
    # A blank black image has no features, should detect 0 faces
    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    face_count, landmarks = detector.detect_faces(blank_frame)
    assert face_count == 0
    assert len(landmarks) == 0
