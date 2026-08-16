import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.models.database import init_db
from app.api import routes_auth, routes_exam, routes_monitor, routes_report
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Initialize FastAPI App
app = FastAPI(
    title="ExamAegis - AI Proctoring System",
    description="FastAPI WebSockets-based Online Exam Proctoring system using Computer Vision.",
    version="1.0.0"
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing/development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup Event: Initialize database tables
@app.on_event("startup")
def on_startup():
    logger.info("Initializing SQLite database...")
    init_db()
    logger.info("Database initialization complete.")

# Include Router Modules
app.include_router(routes_auth.router, prefix="/api")
app.include_router(routes_exam.router, prefix="/api")
app.include_router(routes_monitor.router, prefix="/api")
app.include_router(routes_report.router, prefix="/api")

# Verify frontend directory exists before mounting
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if not os.path.exists(frontend_dir):
    os.makedirs(frontend_dir, exist_ok=True)
    os.makedirs(os.path.join(frontend_dir, "css"), exist_ok=True)
    os.makedirs(os.path.join(frontend_dir, "js"), exist_ok=True)

# Mount frontend directory to serve plain HTML/CSS/JS web pages
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

# Simple health check endpoint (if needed)
@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "ExamAegis Backend"}
