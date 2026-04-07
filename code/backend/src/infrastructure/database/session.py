"""
Database session management for the RiskOptimizer application.
Provides SQLAlchemy session factory and connection pooling.
"""

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

try:
    from sqlalchemy.orm import declarative_base
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base

from src.core.config import config
from src.core.exceptions import DatabaseError, RiskOptimizerException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

_db_url = config.database.url
_is_sqlite = _db_url.startswith("sqlite")

if _is_sqlite:
    engine = create_engine(
        _db_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
        echo=config.api.debug,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

else:
    engine = create_engine(
        _db_url,
        pool_size=config.database.pool_size,
        max_overflow=config.database.max_overflow,
        pool_timeout=config.database.pool_timeout,
        pool_recycle=config.database.pool_recycle,
        pool_pre_ping=True,
        echo=config.api.debug,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Get a database session from the session pool.

    Yields:
        SQLAlchemy session

    Raises:
        DatabaseError: If underlying database operations fail
        RiskOptimizerException: Application exceptions are re-raised unchanged
    """
    session = SessionLocal()
    try:
        logger.debug("Database session created")
        yield session
        session.commit()
        logger.debug("Database session committed")
    except RiskOptimizerException:
        session.rollback()
        raise
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
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}", exc_info=True)
        return False
