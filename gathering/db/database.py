"""
Database connection and management for GatheRing framework.
Extends Pycopg with GatheRing-specific functionality.
"""

import os
from typing import Optional, List, Dict, Any
from functools import lru_cache
from contextlib import contextmanager

try:
    from pycopg import Database as PycopgDatabase, Config
except ImportError:
    # Fallback if pycopg not available - use basic psycopg
    PycopgDatabase = None
    Config = None

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from gathering.db.models import Base


# =============================================================================
# GatheRing Database Class
# =============================================================================


class Database:
    """
    Database wrapper for GatheRing.
    Provides both Pycopg convenience methods and SQLAlchemy ORM access.
    """

    SCHEMA = "gathering"

    def __init__(
        self,
        connection_string: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize database connection.

        Args:
            connection_string: PostgreSQL connection URL
            config: Configuration dict with host, port, database, user, password
        """
        self._connection_string = connection_string or self._build_connection_string(config)
        self._engine = None
        self._session_factory = None
        self._pycopg = None

    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> "Database":
        """
        Create Database from environment variables.

        Looks for:
        - DATABASE_URL (preferred)
        - GATHERING_DATABASE_URL
        - Individual vars: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
        """
        if env_file:
            from dotenv import load_dotenv
            load_dotenv(env_file)

        # Try various env var patterns
        connection_string = (
            os.getenv("GATHERING_DATABASE_URL")
            or os.getenv("DATABASE_URL")
        )

        if connection_string:
            return cls(connection_string=connection_string)

        # Build from individual variables
        config = {
            "host": os.getenv("DB_HOST", os.getenv("PGHOST", "localhost")),
            "port": int(os.getenv("DB_PORT", os.getenv("PGPORT", "5432"))),
            "database": os.getenv("DB_NAME", os.getenv("PGDATABASE", "gathering")),
            "user": os.getenv("DB_USER", os.getenv("PGUSER", "postgres")),
            "password": os.getenv("DB_PASSWORD", os.getenv("PGPASSWORD", "")),
        }

        return cls(config=config)

    @staticmethod
    def _build_connection_string(config: Optional[Dict[str, Any]]) -> str:
        """Build connection string from config dict."""
        if not config:
            config = {}

        host = config.get("host", "localhost")
        port = config.get("port", 5432)
        database = config.get("database", "gathering")
        user = config.get("user", "postgres")
        password = config.get("password", "")

        if password:
            return f"postgresql://{user}:{password}@{host}:{port}/{database}"
        return f"postgresql://{user}@{host}:{port}/{database}"

    # =========================================================================
    # SQLAlchemy Engine & Session
    # =========================================================================

    @property
    def engine(self):
        """Lazy-initialize SQLAlchemy engine."""
        if self._engine is None:
            self._engine = create_engine(
                self._connection_string,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800,
                pool_pre_ping=True,
                echo=os.getenv("SQL_ECHO", "").lower() == "true",
            )
        return self._engine

    @property
    def session_factory(self):
        """Get session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
            )
        return self._session_factory

    @contextmanager
    def session(self) -> Session:
        """
        Get a database session as context manager.

        Usage:
            with db.session() as session:
                session.add(agent)
                session.commit()
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # =========================================================================
    # Pycopg Access (if available)
    # =========================================================================

    @property
    def pycopg(self) -> Optional["PycopgDatabase"]:
        """Get Pycopg database instance for advanced operations."""
        if PycopgDatabase is None:
            return None

        if self._pycopg is None:
            self._pycopg = PycopgDatabase.from_url(self._connection_string)

        return self._pycopg

    # =========================================================================
    # Schema & Initialization
    # =========================================================================

    def ensure_schema(self) -> None:
        """Create the gathering schema if it doesn't exist."""
        with self.engine.connect() as conn:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self.SCHEMA}"))
            conn.commit()

    def init_db(self) -> None:
        """
        Initialize database with all GatheRing tables.
        Creates schema and all tables defined in models.
        """
        self.ensure_schema()
        Base.metadata.create_all(self.engine)

    def drop_all(self, confirm: bool = False) -> None:
        """
        Drop all GatheRing tables. Use with caution!

        Args:
            confirm: Must be True to proceed
        """
        if not confirm:
            raise ValueError("Must pass confirm=True to drop all tables")

        Base.metadata.drop_all(self.engine)

    # =========================================================================
    # Extension Management
    # =========================================================================

    def ensure_extensions(self, extensions: Optional[List[str]] = None) -> None:
        """
        Ensure required PostgreSQL extensions are installed.

        Args:
            extensions: List of extensions to install. Defaults to gathering requirements.
        """
        if extensions is None:
            extensions = ["uuid-ossp"]  # pgvector added when needed

        with self.engine.connect() as conn:
            for ext in extensions:
                try:
                    conn.execute(text(f'CREATE EXTENSION IF NOT EXISTS "{ext}"'))
                    conn.commit()
                except Exception as e:
                    print(f"Warning: Could not create extension {ext}: {e}")

    def enable_pgvector(self) -> bool:
        """
        Enable pgvector extension for semantic search.

        Returns:
            True if enabled successfully, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
            return True
        except Exception as e:
            print(f"Could not enable pgvector: {e}")
            return False

    # =========================================================================
    # Health & Status
    # =========================================================================

    def health_check(self) -> Dict[str, Any]:
        """
        Check database connection and return status.

        Returns:
            Dict with connection status, version, and schema info
        """
        try:
            with self.engine.connect() as conn:
                # Check connection
                result = conn.execute(text("SELECT version()"))
                version = result.scalar()

                # Check schema exists
                result = conn.execute(text(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.schemata "
                    f"WHERE schema_name = '{self.SCHEMA}')"
                ))
                schema_exists = result.scalar()

                # Get table count
                if schema_exists:
                    result = conn.execute(text(
                        f"SELECT COUNT(*) FROM information_schema.tables "
                        f"WHERE table_schema = '{self.SCHEMA}'"
                    ))
                    table_count = result.scalar()
                else:
                    table_count = 0

                return {
                    "status": "healthy",
                    "version": version,
                    "schema_exists": schema_exists,
                    "table_count": table_count,
                }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }

    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics for monitoring.

        Returns:
            Dict with table sizes, row counts, etc.
        """
        stats = {}

        with self.engine.connect() as conn:
            # Get table sizes
            result = conn.execute(text(f"""
                SELECT
                    relname as table_name,
                    pg_size_pretty(pg_total_relation_size(relid)) as size,
                    n_live_tup as row_count
                FROM pg_stat_user_tables
                WHERE schemaname = '{self.SCHEMA}'
                ORDER BY pg_total_relation_size(relid) DESC
            """))

            stats["tables"] = [
                {"name": row[0], "size": row[1], "rows": row[2]}
                for row in result.fetchall()
            ]

            # Get total size
            result = conn.execute(text(f"""
                SELECT pg_size_pretty(
                    SUM(pg_total_relation_size(quote_ident(schemaname) || '.' || quote_ident(tablename)))
                )
                FROM pg_tables
                WHERE schemaname = '{self.SCHEMA}'
            """))
            stats["total_size"] = result.scalar() or "0 bytes"

        return stats

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def execute(self, sql: str, params: Optional[Dict] = None) -> Any:
        """
        Execute raw SQL query.

        Args:
            sql: SQL query string
            params: Query parameters

        Returns:
            Query result
        """
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            conn.commit()
            return result

    def fetch_all(self, sql: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        Execute query and fetch all results as dicts.

        Args:
            sql: SQL query string
            params: Query parameters

        Returns:
            List of row dicts
        """
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]

    def fetch_one(self, sql: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Execute query and fetch one result as dict.

        Args:
            sql: SQL query string
            params: Query parameters

        Returns:
            Row dict or None
        """
        rows = self.fetch_all(sql, params)
        return rows[0] if rows else None

    # =========================================================================
    # Cleanup
    # =========================================================================

    def close(self) -> None:
        """Close all database connections."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
        if self._pycopg:
            # Pycopg handles its own cleanup
            self._pycopg = None

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


# =============================================================================
# Global Database Instance
# =============================================================================

_db_instance: Optional[Database] = None


def init_db(
    connection_string: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    env_file: Optional[str] = None,
) -> Database:
    """
    Initialize the global database instance.

    Args:
        connection_string: PostgreSQL connection URL
        config: Configuration dict
        env_file: Path to .env file

    Returns:
        Database instance
    """
    global _db_instance

    if env_file or (connection_string is None and config is None):
        _db_instance = Database.from_env(env_file)
    else:
        _db_instance = Database(connection_string=connection_string, config=config)

    # Initialize schema and tables
    _db_instance.init_db()

    return _db_instance


def get_db() -> Database:
    """
    Get the global database instance.

    Raises:
        RuntimeError: If database not initialized
    """
    if _db_instance is None:
        raise RuntimeError(
            "Database not initialized. Call init_db() first, "
            "or use Database.from_env() directly."
        )
    return _db_instance


@lru_cache()
def get_db_cached() -> Database:
    """
    Get or create a cached database instance.
    Useful for FastAPI dependency injection.
    """
    return Database.from_env()
