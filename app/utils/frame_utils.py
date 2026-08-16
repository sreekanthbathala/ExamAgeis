import base64
import numpy as np
import cv2

def base64_to_cv2(b64_string: str) -> np.ndarray:
    """
    Converts a base64 encoded image string (potentially with data URL headers)
    into an OpenCV BGR image (numpy array).
    """
    # Remove metadata header if present (e.g., "data:image/jpeg;base64,")
    if "," in b64_string:
        b64_string = b64_string.split(",")[1]
    
    # Decode base64 bytes
    image_bytes = base64.b64decode(b64_string)
    
    # Convert bytes to numpy array
    np_array = np.frombuffer(image_bytes, dtype=np.uint8)
    
    # Decode numpy array to OpenCV BGR image
    image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
    return image

import os
from datetime import datetime

def save_violation_screenshot(frame: np.ndarray, exam_session_id: int, violation_type: str) -> str:
    """
    Saves the current frame as a JPEG screenshot inside `database/screenshots/{session_id}/`.
    Returns the relative URL path `/screenshots/{session_id}/{filename}` for the frontend to load.
    """
    if frame is None:
        return None
    
    try:
        # Create path: database/screenshots/{session_id}/
        dir_path = os.path.join("database", "screenshots", str(exam_session_id))
        os.makedirs(dir_path, exist_ok=True)
        
        # Filename: violation_type_timestamp.jpg
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{violation_type}_{timestamp}.jpg"
        filepath = os.path.join(dir_path, filename)
        
        # Write image to disk
        cv2.imwrite(filepath, frame)
        
        # Return the relative mount path
        return f"/screenshots/{exam_session_id}/{filename}"
    except Exception as e:
        from app.utils.logger import get_logger
        get_logger(__name__).error(f"Error saving screenshot: {e}")
        return None
