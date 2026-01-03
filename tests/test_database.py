"""
Tests for Database module.

Covers:
- Database class initialization
- Connection string building
- Session management
- Health checks
- Schema/extension management
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager


class TestDatabaseInit:
    """Test Database initialization."""

    def test_init_with_connection_string(self):
        """Test initialization with connection string."""
        from gathering.db.database import Database

        db = Database(connection_string="postgresql://user:pass@localhost:5432/testdb")

        assert db._connection_string == "postgresql://user:pass@localhost:5432/testdb"
        assert db._engine is None
        assert db._session_factory is None

    def test_init_with_config(self):
        """Test initialization with config dict."""
        from gathering.db.database import Database

        db = Database(config={
            "host": "myhost",
            "port": 5433,
            "database": "mydb",
            "user": "myuser",
            "password": "mypass"
        })

        assert "myhost" in db._connection_string
        assert "5433" in db._connection_string
        assert "mydb" in db._connection_string
        assert "myuser" in db._connection_string
        assert "mypass" in db._connection_string

    def test_init_with_default_config(self):
        """Test initialization with default config values."""
        from gathering.db.database import Database

        db = Database(config={})

        assert "localhost" in db._connection_string
        assert "5432" in db._connection_string
        assert "gathering" in db._connection_string
        assert "postgres" in db._connection_string


class TestBuildConnectionString:
    """Test connection string building."""

    def test_build_with_password(self):
        """Test building connection string with password."""
        from gathering.db.database import Database

        conn_str = Database._build_connection_string({
            "host": "dbhost",
            "port": 5432,
            "database": "testdb",
            "user": "testuser",
            "password": "secret123"
        })

        assert conn_str == "postgresql://testuser:secret123@dbhost:5432/testdb"

    def test_build_without_password(self):
        """Test building connection string without password."""
        from gathering.db.database import Database

        conn_str = Database._build_connection_string({
            "host": "dbhost",
            "port": 5432,
            "database": "testdb",
            "user": "testuser",
            "password": ""
        })

        assert conn_str == "postgresql://testuser@dbhost:5432/testdb"

    def test_build_with_none_config(self):
        """Test building with None config uses defaults."""
        from gathering.db.database import Database

        conn_str = Database._build_connection_string(None)

        assert "localhost" in conn_str
        assert "5432" in conn_str


class TestFromEnv:
    """Test Database.from_env factory method."""

    @patch.dict(os.environ, {"DATABASE_URL": "postgresql://envuser@localhost/envdb"}, clear=True)
    def test_from_database_url(self):
        """Test from_env uses DATABASE_URL."""
        from gathering.db.database import Database

        db = Database.from_env()

        assert "envuser" in db._connection_string
        assert "envdb" in db._connection_string

    @patch.dict(os.environ, {"GATHERING_DATABASE_URL": "postgresql://gathering@localhost/gatherdb"}, clear=True)
    def test_from_gathering_database_url(self):
        """Test from_env uses GATHERING_DATABASE_URL."""
        from gathering.db.database import Database

        db = Database.from_env()

        assert "gathering" in db._connection_string
        assert "gatherdb" in db._connection_string

    @patch.dict(os.environ, {
        "DB_HOST": "customhost",
        "DB_PORT": "5433",
        "DB_NAME": "customdb",
        "DB_USER": "customuser",
        "DB_PASSWORD": "custompass"
    }, clear=True)
    def test_from_individual_vars(self):
        """Test from_env uses individual DB_* variables."""
        from gathering.db.database import Database

        db = Database.from_env()

        assert "customhost" in db._connection_string
        assert "5433" in db._connection_string
        assert "customdb" in db._connection_string
        assert "customuser" in db._connection_string

    @patch.dict(os.environ, {
        "PGHOST": "pghost",
        "PGPORT": "5434",
        "PGDATABASE": "pgdb",
        "PGUSER": "pguser",
        "PGPASSWORD": "pgpass"
    }, clear=True)
    def test_from_pg_vars(self):
        """Test from_env uses PG* variables as fallback."""
        from gathering.db.database import Database

        db = Database.from_env()

        assert "pghost" in db._connection_string
        assert "5434" in db._connection_string


class TestEngineCreation:
    """Test SQLAlchemy engine creation."""

    @patch("gathering.db.database.create_engine")
    def test_engine_lazy_creation(self, mock_create_engine):
        """Test engine is created lazily."""
        from gathering.db.database import Database

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        db = Database(connection_string="postgresql://test@localhost/testdb")

        # Engine not created yet
        assert db._engine is None

        # Access engine
        engine = db.engine

        # Now it's created
        assert engine == mock_engine
        mock_create_engine.assert_called_once()

    @patch("gathering.db.database.create_engine")
    def test_engine_cached(self, mock_create_engine):
        """Test engine is cached after first access."""
        from gathering.db.database import Database

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        db = Database(connection_string="postgresql://test@localhost/testdb")

        # Access twice
        engine1 = db.engine
        engine2 = db.engine

        # Same instance
        assert engine1 is engine2
        # Only created once
        mock_create_engine.assert_called_once()

    @patch.dict(os.environ, {"DB_POOL_SIZE": "30", "DB_MAX_OVERFLOW": "15"})
    @patch("gathering.db.database.create_engine")
    def test_engine_pool_config_from_env(self, mock_create_engine):
        """Test engine pool configuration from environment."""
        from gathering.db.database import Database

        db = Database(connection_string="postgresql://test@localhost/testdb")
        _ = db.engine

        # Check pool_size and max_overflow were passed
        call_kwargs = mock_create_engine.call_args[1]
        assert call_kwargs["pool_size"] == 30
        assert call_kwargs["max_overflow"] == 15


class TestSessionManagement:
    """Test session context manager."""

    @patch("gathering.db.database.create_engine")
    @patch("gathering.db.database.sessionmaker")
    def test_session_context_manager_success(self, mock_sessionmaker, mock_create_engine):
        """Test session commits on success."""
        from gathering.db.database import Database

        mock_session = Mock()
        mock_session_factory = Mock(return_value=mock_session)
        mock_sessionmaker.return_value = mock_session_factory

        db = Database(connection_string="postgresql://test@localhost/testdb")

        with db.session() as session:
            session.add("something")

        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("gathering.db.database.create_engine")
    @patch("gathering.db.database.sessionmaker")
    def test_session_context_manager_rollback_on_error(self, mock_sessionmaker, mock_create_engine):
        """Test session rollbacks on error."""
        from gathering.db.database import Database

        mock_session = Mock()
        mock_session_factory = Mock(return_value=mock_session)
        mock_sessionmaker.return_value = mock_session_factory

        db = Database(connection_string="postgresql://test@localhost/testdb")

        with pytest.raises(ValueError):
            with db.session() as session:
                raise ValueError("Test error")

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


class TestHealthCheck:
    """Test health check functionality."""

    @patch("gathering.db.database.create_engine")
    def test_health_check_healthy(self, mock_create_engine):
        """Test health check returns healthy status."""
        from gathering.db.database import Database

        # Setup mock
        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)

        # Mock execute results
        mock_result1 = Mock()
        mock_result1.scalar.return_value = "PostgreSQL 15.0"

        mock_result2 = Mock()
        mock_result2.scalar.return_value = True

        mock_result3 = Mock()
        mock_result3.scalar.return_value = 44

        mock_conn.execute.side_effect = [mock_result1, mock_result2, mock_result3]

        mock_engine = Mock()
        mock_engine.connect.return_value = mock_conn
        mock_create_engine.return_value = mock_engine

        db = Database(connection_string="postgresql://test@localhost/testdb")
        result = db.health_check()

        assert result["status"] == "healthy"
        assert "PostgreSQL" in result["version"]
        assert result["schema_exists"] is True
        assert result["table_count"] == 44

    @patch("gathering.db.database.create_engine")
    def test_health_check_unhealthy(self, mock_create_engine):
        """Test health check returns unhealthy on connection error."""
        from gathering.db.database import Database

        mock_engine = Mock()
        mock_engine.connect.side_effect = Exception("Connection refused")
        mock_create_engine.return_value = mock_engine

        db = Database(connection_string="postgresql://test@localhost/testdb")
        result = db.health_check()

        assert result["status"] == "unhealthy"
        assert "Connection refused" in result["error"]


class TestSchemaManagement:
    """Test schema and table management."""

    @patch("gathering.db.database.create_engine")
    def test_ensure_schema(self, mock_create_engine):
        """Test ensure_schema creates schema."""
        from gathering.db.database import Database

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)

        mock_engine = Mock()
        mock_engine.connect.return_value = mock_conn
        mock_create_engine.return_value = mock_engine

        db = Database(connection_string="postgresql://test@localhost/testdb")
        db.ensure_schema()

        # Check SQL was executed
        mock_conn.execute.assert_called()
        mock_conn.commit.assert_called()

    @patch("gathering.db.database.create_engine")
    def test_drop_all_requires_confirm(self, mock_create_engine):
        """Test drop_all requires confirmation."""
        from gathering.db.database import Database

        db = Database(connection_string="postgresql://test@localhost/testdb")

        with pytest.raises(ValueError, match="confirm=True"):
            db.drop_all()

    @patch("gathering.db.database.Base")
    @patch("gathering.db.database.create_engine")
    def test_drop_all_with_confirm(self, mock_create_engine, mock_base):
        """Test drop_all works with confirmation."""
        from gathering.db.database import Database

        db = Database(connection_string="postgresql://test@localhost/testdb")
        db.drop_all(confirm=True)

        mock_base.metadata.drop_all.assert_called_once()


class TestExtensionManagement:
    """Test PostgreSQL extension management."""

    @patch("gathering.db.database.create_engine")
    def test_ensure_extensions(self, mock_create_engine):
        """Test ensure_extensions installs extensions."""
        from gathering.db.database import Database

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)

        mock_engine = Mock()
        mock_engine.connect.return_value = mock_conn
        mock_create_engine.return_value = mock_engine

        db = Database(connection_string="postgresql://test@localhost/testdb")
        db.ensure_extensions(["uuid-ossp", "vector"])

        # Should have called execute twice (once per extension)
        assert mock_conn.execute.call_count == 2
        assert mock_conn.commit.call_count == 2

    @patch("gathering.db.database.create_engine")
    def test_enable_pgvector_success(self, mock_create_engine):
        """Test enable_pgvector returns True on success."""
        from gathering.db.database import Database

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)

        mock_engine = Mock()
        mock_engine.connect.return_value = mock_conn
        mock_create_engine.return_value = mock_engine

        db = Database(connection_string="postgresql://test@localhost/testdb")
        result = db.enable_pgvector()

        assert result is True

    @patch("gathering.db.database.create_engine")
    def test_enable_pgvector_failure(self, mock_create_engine):
        """Test enable_pgvector returns False on failure."""
        from gathering.db.database import Database

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.execute.side_effect = Exception("Extension not available")

        mock_engine = Mock()
        mock_engine.connect.return_value = mock_conn
        mock_create_engine.return_value = mock_engine

        db = Database(connection_string="postgresql://test@localhost/testdb")
        result = db.enable_pgvector()

        assert result is False


class TestConvenienceMethods:
    """Test convenience methods."""

    @patch("gathering.db.database.create_engine")
    def test_execute_raw_sql(self, mock_create_engine):
        """Test executing raw SQL."""
        from gathering.db.database import Database

        mock_result = Mock()
        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.execute.return_value = mock_result

        mock_engine = Mock()
        mock_engine.connect.return_value = mock_conn
        mock_create_engine.return_value = mock_engine

        db = Database(connection_string="postgresql://test@localhost/testdb")
        result = db.execute("SELECT * FROM agents WHERE id = :id", {"id": 1})

        assert result == mock_result
        mock_conn.commit.assert_called_once()


class TestDatabaseStats:
    """Test database statistics."""

    @patch("gathering.db.database.create_engine")
    def test_get_stats(self, mock_create_engine):
        """Test getting database statistics."""
        from gathering.db.database import Database

        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)

        # Mock table stats result
        mock_result1 = Mock()
        mock_result1.fetchall.return_value = [
            ("agents", "1 MB", 100),
            ("memories", "5 MB", 1000),
        ]

        # Mock total size result
        mock_result2 = Mock()
        mock_result2.scalar.return_value = "10 MB"

        mock_conn.execute.side_effect = [mock_result1, mock_result2]

        mock_engine = Mock()
        mock_engine.connect.return_value = mock_conn
        mock_create_engine.return_value = mock_engine

        db = Database(connection_string="postgresql://test@localhost/testdb")
        stats = db.get_stats()

        assert "tables" in stats
        assert len(stats["tables"]) == 2
        assert stats["tables"][0]["name"] == "agents"
        assert stats["total_size"] == "10 MB"


class TestPycopgIntegration:
    """Test Pycopg integration."""

    def test_pycopg_none_when_not_available(self):
        """Test pycopg property returns None when not available."""
        from gathering.db.database import Database

        with patch("gathering.db.database.PycopgDatabase", None):
            db = Database(connection_string="postgresql://test@localhost/testdb")
            # Re-patch after import
            import gathering.db.database as db_module
            original = db_module.PycopgDatabase
            db_module.PycopgDatabase = None

            try:
                assert db.pycopg is None
            finally:
                db_module.PycopgDatabase = original
