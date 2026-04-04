"""SQLAlchemy engine and session factory (PostgreSQL or SQLite)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import get_db_engine_kwargs, get_settings, is_sqlite

settings = get_settings()
DATABASE_URL = settings.DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    **get_db_engine_kwargs(DATABASE_URL),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
