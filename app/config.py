import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Settings
    SECRET_KEY: str = "supersecretkeyforexamaegisprojectviva2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    # Database
    DATABASE_URL: str = "sqlite:///database/exam_aegis.db"

    # ML Model Paths
    YOLO_MODEL_PATH: str = "ml_models/yolov8n.pt"
    DLIB_PREDICTOR_PATH: str = "ml_models/shape_predictor_68_face_landmarks.dat"

    # Proctoring Core Thresholds
    EYE_GAZE_MIN: float = 0.35
    EYE_GAZE_MAX: float = 0.65
    BLINK_EAR_THRESHOLD: float = 0.20
    BLINK_DURATION_THRESHOLD_SEC: float = 3.0
    HEAD_POSE_YAW_THRESHOLD: float = 20.0
    HEAD_POSE_PITCH_THRESHOLD: float = 15.0
    MOUTH_MAR_THRESHOLD: float = 0.50
    AUDIO_RMS_THRESHOLD: float = 0.03
    OBJECT_CONF_THRESHOLD: float = 0.45

    # Integrity Score Weights
    VIOLATION_WEIGHT_LOW: int = 1
    VIOLATION_WEIGHT_MEDIUM: int = 3
    VIOLATION_WEIGHT_HIGH: int = 7

    # Configuration for loading environment file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
