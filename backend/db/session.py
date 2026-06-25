from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base

# Using SQLite for local development
DATABASE_URL = "sqlite:///./healthcare_copilot.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Creates the tables in the database."""
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized.")

def get_db():
    """Yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()