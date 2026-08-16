import numpy as np
from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)

# Try importing ultralytics
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logger.warning("Ultralytics YOLO package is not installed. Object detection will be unavailable/mocked.")

class ObjectDetector:
    def __init__(self, model_path: str = None):
        self.model = None
        if YOLO_AVAILABLE:
            try:
                # Use configured model path, fall back to "yolov8n.pt" which auto-downloads if missing
                path = model_path or settings.YOLO_MODEL_PATH
                logger.info(f"Loading YOLOv8 model from: {path}")
                self.model = YOLO(path)
                logger.info("YOLOv8 model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load YOLOv8 model: {e}")
                # Try default auto-download fallback
                try:
                    logger.info("Attempting to load default yolov8n.pt...")
                    self.model = YOLO("yolov8n.pt")
                except Exception as ex:
                    logger.error(f"YOLOv8 fallback also failed: {ex}")
                    self.model = None

    def detect_objects(self, frame: np.ndarray, conf_threshold: float = 0.45):
        """
        Runs YOLOv8 object detection on the frame.
        Detects: person, cell phone, book, laptop.
        Returns:
        - detections (list of dicts): list containing label, confidence, and bounding box
        - person_count (int): number of persons detected in the frame.
        """
        if frame is None or not self.model:
            return [], 0

        detections = []
        person_count = 0

        try:
            # Run prediction
            results = self.model.predict(
                frame,
                conf=conf_threshold,
                verbose=False,
                classes=[0, 63, 67, 73]  # 0: person, 63: laptop, 67: cell phone, 73: book in COCO
            )

            for result in results:
                boxes = result.boxes
                for box in boxes:
                    class_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    label = self.model.names[class_id]
                    
                    # Extract bounding box [x1, y1, x2, y2]
                    xyxy = box.xyxy[0].tolist()
                    
                    if label == "person":
                        person_count += 1
                    
                    detections.append({
                        "label": label,
                        "confidence": conf,
                        "box": xyxy
                    })

            return detections, person_count
        except Exception as e:
            logger.error(f"Error during YOLOv8 prediction: {e}")
            return [], 0
