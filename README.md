# ExamAegis - AI-Based Online Exam Proctoring System

ExamAegis is a complete, real-time AI-based online exam proctoring system built using Python **FastAPI** (async backend), native **WebSockets**, and computer vision libraries. It processes webcam video frames and browser microphone audio streams to detect academic dishonesty patterns.

---

## Key Features

1. **Authentication:**
   - Student authorization via Name, Roll Number, and Exam ID (registers dynamic student profiles).
   - Instructor/Admin login for reviewing log entries.
2. **Real-time Camera Proctoring:**
   - **Face Counting:** Detects if 0, 1, or multiple faces are visible.
   - **Eye Gaze Tracking:** Estimates pupil center deviation relative to eye corners to flag looking away.
   - **Blink & Sleep Detection:** Measures Eye Aspect Ratio (EAR) to detect sustained eye closure/sleeping.
   - **Head Pose Estimation:** Uses `solvePnP` to calculate Yaw, Pitch, and Roll of the head to detect looking away.
   - **Mouth Tracking:** Measures Mouth Aspect Ratio (MAR) to detect speaking.
   - **Object Detection:** Integrates YOLOv8 to detect forbidden items (cell phones, books, secondary screens).
3. **Real-time Audio Proctoring:**
   - Capture microphone audio chunk streams from the client browser and analyze decibel energy (RMS) via **Librosa** to flag voice activity.
4. **Proctor Violation Engine:**
   - Applies configurable temporal thresholds (e.g., no face for > 5s, gaze away for > 3s) and logs violations with low/medium/high severity ratings.
   - Live socket feedback displays warnings back to the candidate (e.g., "Please face the camera").
5. **Admin Control Panel:**
   - Browse proctored exam sessions.
   - Review interactive visual violation timelines with timestamps.
   - Export structured logs as JSON reports.

---

## Project Structure

```
ExamAegis/
├── app/
│   ├── main.py                     # Entry point & Static folder mounting
│   ├── config.py                   # Configuration settings & thresholds
│   ├── api/                        # Route Handlers
│   │   ├── routes_auth.py          # Student & admin authentication
│   │   ├── routes_exam.py          # Session management (start/end)
│   │   ├── routes_monitor.py       # Live WebSocket for image/audio frames
│   │   └── routes_report.py        # Violation details & exports
│   ├── core/                       # Computer Vision & Audio analyzers
│   │   ├── face_detection.py       # Counts faces (Mediapipe / Dlib fallback)
│   │   ├── eye_gaze.py             # Computes pupil location ratio
│   │   ├── blink_detection.py      # Computes Eye Aspect Ratio (EAR)
│   │   ├── head_pose.py            # Head yaw & pitch rotation
│   │   ├── mouth_tracking.py       # Computes Mouth Aspect Ratio (MAR)
│   │   ├── object_detection.py     # YOLOv8 object detector
│   │   ├── audio_detection.py      # Librosa audio RMS level check
│   │   └── violation_engine.py     # State tracker, cooldowns, & DB writer
│   ├── models/                     # SQLModel DB Schema definitions
│   │   ├── database.py             # Engine initialization & admin seeder
│   │   ├── student.py
│   │   ├── exam_session.py
│   │   └── violation_log.py
│   ├── schemas/                    # Pydantic Schemas
│   │   ├── auth_schema.py
│   │   ├── exam_schema.py
│   │   └── violation_schema.py
│   └── utils/                      # Helper scripts
│       ├── frame_utils.py          # Base64 decoder
│       └── logger.py
├── ml_models/                      # Directory for YOLO and Dlib models
├── frontend/                       # Client web pages
│   ├── index.html                  # Student proctoring interface
│   ├── admin_dashboard.html        # Admin review dashboard
│   ├── css/style.css
│   └── js/
│       ├── webcam.js               # getUserMedia helper
│       ├── socket_client.js        # WS connection & audio chunking
│       └── dashboard.js            # Dashboard rendering
├── database/                       # Location for generated SQLite database
├── tests/                          # Automated PyTest unit tests
│   ├── test_face_detection.py
│   ├── test_object_detection.py
│   └── test_routes.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Setup Instructions (Ubuntu Linux)

Execute the following commands in your Ubuntu terminal:

### 1. Install System Dependencies
Dlib and PyAudio compilation require C++ build tools and audio libraries:
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv cmake build-essential libportaudio2 libasound2-dev python3-dev wget bzip2
```

### 2. Set Up Virtual Environment
Clone this repository, navigate to the folder, and create the environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Download ML Model Weights
Download YOLOv8 weights and Dlib shape predictor models directly into the `ml_models` folder:

*   **YOLOv8 Weights:** (Note: The application will automatically download `yolov8n.pt` if missing, but you can pre-fetch it here)
    ```bash
    wget https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt -O ml_models/yolov8n.pt
    ```

*   **Dlib Face Landmark Model:**
    ```bash
    wget http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2
    bunzip2 shape_predictor_68_face_landmarks.dat.bz2
    mv shape_predictor_68_face_landmarks.dat ml_models/
    ```

---

## Configuration & Environment Variables

Copy `.env.example` to `.env` and adjust thresholds if necessary:
```bash
cp .env.example .env
```
Default configuration file settings:
*   `EYE_GAZE_MIN` & `EYE_GAZE_MAX` (0.35 to 0.65): Normal range. Outside this represents looking away.
*   `BLINK_EAR_THRESHOLD` (0.20): Eye Aspect Ratio limit for closed eyes.
*   `HEAD_POSE_YAW_THRESHOLD` (20.0°): Left/Right head turn limit.
*   `HEAD_POSE_PITCH_THRESHOLD` (15.0°): Up/Down head rotation limit.
*   `MOUTH_MAR_THRESHOLD` (0.50): Mouth open limit (talking).
*   `AUDIO_RMS_THRESHOLD` (0.03): Noise/voice threshold.

---

## Running the Server

Start the FastAPI application using Uvicorn:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser:
*   **Student Exam Room:** `http://localhost:8000/index.html` (or `http://localhost:8000/` directly)
*   **Instructor Dashboard:** `http://localhost:8000/admin_dashboard.html`
*   **Interactive API documentation (Swagger UI):** `http://localhost:8000/docs`

### Seed Credentials
*   **Admin Username:** `admin`
*   **Admin Password:** `admin123`
*   **Student Login:** Enter any Name, Email, Exam ID, and Roll Number (new students register automatically).

---

## Running Tests

Verify that your computer vision fallbacks, endpoint routing, and authentication flows work correctly:
```bash
pytest
```
All route tests use an in-memory SQLite database, keeping development and test environments fully isolated.
