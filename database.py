import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Load variables from .env in the project root
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing. Please define it in your .env file.")

# Normalize SQLAlchemy driver prefix if provided as 'postgres://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Connection pool settings optimized for PostgreSQL / Neon
engine = create_engine(
    DATABASE_URL,
    pool_size=15,
    max_overflow=25,
    pool_recycle=1800,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency helper for database session lifecycles."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()