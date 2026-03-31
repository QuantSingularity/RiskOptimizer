from typing import Any
from unittest.mock import MagicMock, patch

from db.database import Database


class MockDatabaseError(BaseException):
    pass


@patch("db.database.psycopg2")
def test_database_connect_success(mock_psycopg2: Any) -> Any:
    """Test successful database connection."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_psycopg2.connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_psycopg2.DatabaseError = MockDatabaseError
    db = Database()
    assert db.connection is None
    assert db.cursor is None
    result = db.connect()
    assert result is True
    assert db.connection == mock_conn
    assert db.cursor == mock_cursor
    mock_psycopg2.connect.assert_called_once()
    mock_conn.cursor.assert_called_once()


@patch("db.database.psycopg2")
def test_database_connect_failure(mock_psycopg2: Any) -> Any:
    """Test database connection failure."""
    mock_psycopg2.DatabaseError = MockDatabaseError
    mock_psycopg2.connect.side_effect = MockDatabaseError("Connection failed")
    db = Database()
    result = db.connect()
    assert result is False
    assert db.connection is None
    assert db.cursor is None
    mock_psycopg2.connect.assert_called_once()


@patch("db.database.psycopg2")
def test_database_disconnect(mock_psycopg2: Any) -> Any:
    """Test disconnecting from the database."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_psycopg2.connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_psycopg2.DatabaseError = MockDatabaseError
    db = Database()
    db.connect()
    assert db.connection is not None
    assert db.cursor is not None
    db.disconnect()
    assert db.connection is None
    assert db.cursor is None
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch("db.database.psycopg2")
def test_execute_query_select_success(mock_psycopg2: Any) -> Any:
    """Test executing a SELECT query successfully."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_psycopg2.connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [{"id": 1, "name": "test"}]
    mock_psycopg2.DatabaseError = MockDatabaseError
    db = Database()
    db.connect()
    query = "SELECT * FROM users WHERE id = %s"
    params = (1,)
    result = db.execute_query(query, params)
    assert result == [{"id": 1, "name": "test"}]
    mock_cursor.execute.assert_called_once_with(query, params)
    mock_cursor.fetchall.assert_called_once()
    mock_conn.commit.assert_not_called()


@patch("db.database.psycopg2")
def test_execute_query_insert_success(mock_psycopg2: Any) -> Any:
    """Test executing an INSERT query successfully."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_psycopg2.connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_psycopg2.DatabaseError = MockDatabaseError
    db = Database()
    db.connect()
    query = "INSERT INTO users (name) VALUES (%s)"
    params = ("new_user",)
    result = db.execute_query(query, params)
    assert result is True
    mock_cursor.execute.assert_called_once_with(query, params)
    mock_cursor.fetchall.assert_not_called()
    mock_conn.commit.assert_called_once()


@patch("db.database.psycopg2")
def test_execute_query_error(mock_psycopg2: Any) -> Any:
    """Test handling of query execution error."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_psycopg2.connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_psycopg2.DatabaseError = MockDatabaseError
    mock_cursor.execute.side_effect = MockDatabaseError("Query failed")
    db = Database()
    db.connect()
    query = "SELECT * FROM non_existent_table"
    result = db.execute_query(query)
    assert result is None
    mock_cursor.execute.assert_called_once_with(query, None)
    mock_conn.rollback.assert_called_once()
    mock_conn.commit.assert_not_called()


@patch.object(Database, "execute_query")
def test_get_portfolio_success(mock_execute_query: Any) -> Any:
    """Test get_portfolio successfully retrieves data."""
    mock_address = "0x123"
    mock_data = [
        {
            "id": 1,
            "user_address": mock_address,
            "created_at": None,
            "asset_symbol": "ETH",
            "percentage": 0.6,
        },
        {
            "id": 1,
            "user_address": mock_address,
            "created_at": None,
            "asset_symbol": "BTC",
            "percentage": 0.4,
        },
    ]
    mock_execute_query.return_value = mock_data
    db = Database()
    result = db.get_portfolio(mock_address)
    assert result == mock_data
    expected_query = "\n        SELECT p.id, p.user_address, p.created_at,\n               a.asset_symbol, a.percentage\n        FROM portfolios p\n        LEFT JOIN allocations a ON p.id = a.portfolio_id\n        WHERE p.user_address = %s\n        "
    mock_execute_query.assert_called_once_with(expected_query, (mock_address,))


@patch.object(Database, "execute_query")
def test_get_portfolio_not_found(mock_execute_query: Any) -> Any:
    """Test get_portfolio when user has no portfolio."""
    mock_address = "0x456"
    mock_execute_query.return_value = []
    db = Database()
    result = db.get_portfolio(mock_address)
    assert result == []
    mock_execute_query.assert_called_once()


@patch("db.database.psycopg2")
def test_save_portfolio_new(mock_psycopg2: Any) -> Any:
    """Test saving a new portfolio."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_psycopg2.connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_psycopg2.DatabaseError = MockDatabaseError
    mock_cursor.fetchone.side_effect = [None, {"id": 5}]
    db = Database()
    db.connect()
    user_address = "0xNEW"
    allocations = {"AAPL": 0.7, "GOOG": 0.3}
    result = db.save_portfolio(user_address, allocations)
    assert result is True
    assert mock_cursor.execute.call_count == 4
    mock_cursor.execute.assert_any_call(
        "SELECT id FROM portfolios WHERE user_address = %s", (user_address,)
    )
    mock_cursor.execute.assert_any_call(
        "INSERT INTO portfolios (user_address) VALUES (%s) RETURNING id",
        (user_address,),
    )
    mock_cursor.execute.assert_any_call(
        "INSERT INTO allocations (portfolio_id, asset_symbol, percentage) VALUES (%s, %s, %s)",
        (5, "AAPL", 0.7),
    )
    mock_cursor.execute.assert_any_call(
        "INSERT INTO allocations (portfolio_id, asset_symbol, percentage) VALUES (%s, %s, %s)",
        (5, "GOOG", 0.3),
    )
    mock_conn.commit.assert_called_once()


@patch("db.database.psycopg2")
def test_save_portfolio_update(mock_psycopg2: Any) -> Any:
    """Test updating an existing portfolio."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_psycopg2.connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_psycopg2.DatabaseError = MockDatabaseError
    mock_cursor.fetchone.return_value = {"id": 10}
    db = Database()
    db.connect()
    user_address = "0xUPDATE"
    allocations = {"MSFT": 1.0}
    result = db.save_portfolio(user_address, allocations)
    assert result is True
    assert mock_cursor.execute.call_count == 3
    mock_cursor.execute.assert_any_call(
        "SELECT id FROM portfolios WHERE user_address = %s", (user_address,)
    )
    mock_cursor.execute.assert_any_call(
        "DELETE FROM allocations WHERE portfolio_id = %s", (10,)
    )
    mock_cursor.execute.assert_any_call(
        "INSERT INTO allocations (portfolio_id, asset_symbol, percentage) VALUES (%s, %s, %s)",
        (10, "MSFT", 1.0),
    )
    mock_conn.commit.assert_called_once()


@patch("db.database.psycopg2")
def test_save_portfolio_error(mock_psycopg2: Any) -> Any:
    """Test error handling during portfolio save."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_psycopg2.connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_psycopg2.DatabaseError = MockDatabaseError
    mock_cursor.execute.side_effect = MockDatabaseError("Save failed")
    db = Database()
    db.connect()
    user_address = "0xFAIL"
    allocations = {"FAIL": 1.0}
    result = db.save_portfolio(user_address, allocations)
    assert result is False
    mock_conn.rollback.assert_called_once()
    mock_conn.commit.assert_not_called()
