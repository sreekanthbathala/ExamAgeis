import os
from sqlmodel import SQLModel, create_engine, Session, text
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Parse the database URL to get file path if it is sqlite
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:///"):
    db_path = db_url.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

# Create engine (sqlite requires check_same_thread=False for multiple threads/websockets)
connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
engine = create_engine(db_url, connect_args=connect_args)

def init_db():
    # Import all models to register them on SQLModel.metadata
    from app.models.student import Student
    from app.models.exam_session import ExamSession
    from app.models.violation_log import ViolationLog
    
    SQLModel.metadata.create_all(engine)
    
    # Run automatic table migration for screenshot_path column
    with Session(engine) as session:
        try:
            # Check if column exists
            session.execute(text("SELECT screenshot_path FROM violationlog LIMIT 1"))
        except Exception:
            # Column is missing, add it
            try:
                logger.info("Migrating database: adding 'screenshot_path' column to violationlog table.")
                session.rollback()
                session.execute(text("ALTER TABLE violationlog ADD COLUMN screenshot_path VARCHAR"))
                session.commit()
                logger.info("Database migration successful.")
            except Exception as migrate_err:
                logger.error(f"Failed to migrate database columns: {migrate_err}")

    # Initialize default admin if not present
    seed_default_admin()

def get_db():
    with Session(engine) as session:
        yield session

def seed_default_admin():
    from app.models.student import Student
    import bcrypt
    
    with Session(engine) as session:
        # Check if default admin student/user exists
        # To handle admin login simply, let's look for a student record or a separate user table.
        # Wait, the prompt says Admin Login: (username, password).
        # We can store the admin in the Student table with a special role or flag,
        # or just hardcode the admin credentials in config/env or look for special roll_number 'ADMIN'.
        # Let's create an ADMIN student, or use a hardcoded check, or store them in a simple way.
        # Storing in Student table with name="Admin", roll_number="ADMIN", email="admin@examaegis.com" is perfect
        # and we can store their hashed password there too. Let's check!
        admin = session.query(Student).filter(Student.roll_number == "ADMIN").first()
        if not admin:
            hashed = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode('utf-8')
            admin_user = Student(
                name="System Administrator",
                roll_number="ADMIN",
                email="admin@examaegis.com",
                hashed_password=hashed
            )
            session.add(admin_user)
            session.commit()
