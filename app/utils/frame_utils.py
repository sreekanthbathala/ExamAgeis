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
