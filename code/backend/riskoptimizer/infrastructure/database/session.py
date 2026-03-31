"""
Database session management for the RiskOptimizer application.
Provides SQLAlchemy session factory and connection pooling.
"""

import logging
from contextlib import contextmanager
from typing import Generator

from riskoptimizer.core.config import config
from riskoptimizer.core.exceptions import DatabaseError
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    config.database.url,
    pool_size=config.database.pool_size,
    max_overflow=config.database.max_overflow,
    pool_timeout=config.database.pool_timeout,
    pool_recycle=config.database.pool_recycle,
    pool_pre_ping=True,  # Verify connections before using them
    echo=config.api.debug,  # Log SQL queries in debug mode
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all SQLAlchemy models
Base = declarative_base()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Get a database session from the session pool.

    Yields:
        SQLAlchemy session

    Raises:
        DatabaseError: If database operations fail
    """
    session = SessionLocal()
    try:
        logger.debug("Database session created")
        yield session
        session.commit()
        logger.debug("Database session committed")
    except Exception as e:
        session.rollback()
        logger.error(f"Database error: {str(e)}", exc_info=True)
        raise DatabaseError(f"Database operation failed: {str(e)}")
    finally:
        session.close()
        logger.debug("Database session closed")


def init_db() -> None:
    """
    Initialize database by creating all tables.

    This should be called during application startup.
    """
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}", exc_info=True)
        raise DatabaseError(f"Failed to initialize database: {str(e)}")


def check_db_connection() -> bool:
    """
    Check database connection.

    Returns:
        True if connection is successful, False otherwise
    """
    try:
        # Execute a simple query to check connection
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}", exc_info=True)
        return False
