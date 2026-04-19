"""
Database layer tests for RiskOptimizer.

Tests the SQLAlchemy session management and model definitions
using a transient in-memory SQLite database.
"""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_engine():
    return create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )


def _make_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()


def _create_tables(engine):
    from src.infrastructure.database.models import Base

    Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Session management tests
# ---------------------------------------------------------------------------


def test_engine_creation() -> object:
    """Test that an in-memory SQLite engine can be created."""
    engine = _make_engine()
    assert engine is not None
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.fetchone()[0] == 1


def test_session_commit_rollback() -> object:
    """Test session commit and rollback behave correctly."""
    engine = _make_engine()
    _create_tables(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()
    try:
        session.execute(text("SELECT 1"))
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def test_get_db_session_context_manager() -> object:
    """Test that get_db_session yields a session and commits on clean exit."""
    with patch("src.infrastructure.database.session.SessionLocal") as mock_factory:
        mock_session = MagicMock()
        mock_factory.return_value = mock_session
        from src.infrastructure.database.session import get_db_session

        with get_db_session() as session:
            assert session is mock_session
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()


def test_get_db_session_rolls_back_on_error() -> object:
    """Test that get_db_session rolls back when an exception occurs."""
    with patch("src.infrastructure.database.session.SessionLocal") as mock_factory:
        mock_session = MagicMock()
        mock_factory.return_value = mock_session
        from src.core.exceptions import DatabaseError
        from src.infrastructure.database.session import get_db_session

        with pytest.raises(DatabaseError):
            with get_db_session() as session:
                raise RuntimeError("simulated error")
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


# ---------------------------------------------------------------------------
# Model table creation tests
# ---------------------------------------------------------------------------


def test_all_tables_created() -> object:
    """Test that all expected tables are created by Base.metadata.create_all."""
    engine = _make_engine()
    _create_tables(engine)
    from sqlalchemy import inspect

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    expected = {
        "users",
        "portfolios",
        "allocations",
        "risk_assessments",
        "market_data",
        "optimization_results",
        "task_results",
        "audit_logs",
    }
    for table in expected:
        assert table in tables, f"Expected table '{table}' not found"


def test_user_model_columns() -> object:
    """Test the User model has required columns."""
    engine = _make_engine()
    _create_tables(engine)
    from sqlalchemy import inspect

    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("users")}
    for expected_col in (
        "id",
        "email",
        "username",
        "hashed_password",
        "is_active",
        "role",
    ):
        assert expected_col in cols, f"Column '{expected_col}' missing from users table"


def test_portfolio_model_columns() -> object:
    """Test the Portfolio model has required columns."""
    engine = _make_engine()
    _create_tables(engine)
    from sqlalchemy import inspect

    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("portfolios")}
    for expected_col in ("id", "user_id", "user_address", "name", "total_value"):
        assert (
            expected_col in cols
        ), f"Column '{expected_col}' missing from portfolios table"


def test_allocation_model_columns() -> object:
    """Test the Allocation model has required columns."""
    engine = _make_engine()
    _create_tables(engine)
    from sqlalchemy import inspect

    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("allocations")}
    for expected_col in ("id", "portfolio_id", "asset_symbol", "percentage"):
        assert (
            expected_col in cols
        ), f"Column '{expected_col}' missing from allocations table"


# ---------------------------------------------------------------------------
# check_db_connection tests
# ---------------------------------------------------------------------------


def test_check_db_connection_success() -> object:
    """Test check_db_connection returns True on healthy engine."""
    with patch("src.infrastructure.database.session.engine") as mock_engine:
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = MagicMock()
        from src.infrastructure.database.session import check_db_connection

        result = check_db_connection()
        assert result is True


def test_check_db_connection_failure() -> object:
    """Test check_db_connection returns False when engine raises."""
    with patch("src.infrastructure.database.session.engine") as mock_engine:
        mock_engine.connect.side_effect = Exception("Connection refused")
        from src.infrastructure.database.session import check_db_connection

        result = check_db_connection()
        assert result is False
