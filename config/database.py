
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv


# Load .env from project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")


# Get database URL.
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is not set"
    )


# Explicitly use the existing psycopg2 driver.
database_url = make_url(DATABASE_URL)

if database_url.drivername in ("postgresql", "postgres"):
    database_url = database_url.set(
        drivername="postgresql+psycopg2"
    )


# Create database engine.
engine = create_engine(
    database_url,
    pool_pre_ping=True
)


# Create session factory.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# Base class for database models.
Base = declarative_base()


# Database session generator.
def get_db():
    """
    Create a database session and close it automatically.
    """

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()
