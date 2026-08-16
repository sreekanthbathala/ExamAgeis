import pytest
import numpy as np
from app.core.object_detection import ObjectDetector

def test_object_detector_init():
    # Instantiate without crash
    detector = ObjectDetector()
    assert detector is not None

def test_detect_objects_empty_frame():
    detector = ObjectDetector()
    # Passing None should return empty detections and count 0
    detections, person_count = detector.detect_objects(None)
    assert len(detections) == 0
    assert person_count == 0

def test_detect_objects_black_image():
    detector = ObjectDetector()
    # Blank frame should run prediction and return 0 persons/objects
    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    detections, person_count = detector.detect_objects(blank_frame)
    assert len(detections) == 0
    assert person_count == 0
