"""
Database Connection & Session Management
Ask MAGIK - Phase 1 Foundation

Provides a dialect-agnostic database engine and session factory.
Supports both SQLite (local development/prototype) and PostgreSQL (production).
"""

from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.config import settings

# Configure engine parameters depending on dialect
connect_args = {}
engine_kwargs = {}

if settings.is_sqlite:
    # SQLite requires check_same_thread=False for multi-threaded FastAPI usage
    connect_args["check_same_thread"] = False
else:
    # Production connection pool settings for PostgreSQL
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
    })

# Create SQLAlchemy engine
engine = create_engine(
    settings.resolved_database_url,
    connect_args=connect_args,
    **engine_kwargs,
)

# Enable foreign key enforcement on SQLite connections
if settings.is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency generator for FastAPI and service operations.
    Ensures sessions are closed reliably after each request/context.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
