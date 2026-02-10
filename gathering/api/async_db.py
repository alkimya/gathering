"""
Async database service for FastAPI using pycopg AsyncPooledDatabase.

Provides non-blocking database access for async route handlers.
The sync DatabaseService in dependencies.py remains for non-async contexts
(CLI, migrations, scripts). Route handlers should prefer this async service.
"""

import os
import logging
from typing import Dict, List, Optional

from pycopg import AsyncPooledDatabase, Config as PycopgConfig

logger = logging.getLogger(__name__)


class AsyncDatabaseService:
    """Async database service singleton using pycopg AsyncPooledDatabase.

    Lifecycle:
        1. get_instance() creates the singleton (parses env, creates pool object)
        2. startup() opens the pool (must be awaited in FastAPI lifespan)
        3. execute/fetch methods run queries without blocking the event loop
        4. shutdown() closes the pool (must be awaited in lifespan shutdown)
    """

    _instance: Optional['AsyncDatabaseService'] = None

    @classmethod
    def get_instance(cls) -> 'AsyncDatabaseService':
        """Get or create the singleton AsyncDatabaseService instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for test isolation)."""
        cls._instance = None

    def __init__(self):
        from dotenv import load_dotenv
        load_dotenv()

        # Support DATABASE_URL (used in CI) or individual DB_* vars
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            config = PycopgConfig.from_url(database_url)
        else:
            config = PycopgConfig(
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', '5432')),
                database=os.getenv('DB_NAME', 'gathering'),
                user=os.getenv('DB_USER', 'loc'),
                password=os.getenv('DB_PASSWORD', ''),
            )

        self._pool = AsyncPooledDatabase(config, min_size=4, max_size=20)

    async def startup(self) -> None:
        """Open the async connection pool. Call during FastAPI lifespan startup."""
        await self._pool.open()
        logger.info("Async database pool opened")

    async def shutdown(self) -> None:
        """Close the async connection pool. Call during FastAPI lifespan shutdown."""
        await self._pool.close()
        logger.info("Async database pool closed")

    async def execute(self, sql: str, params: Optional[Dict] = None) -> List[Dict]:
        """Execute query and return list of dicts (non-blocking)."""
        return await self._pool.execute(sql, params or {})

    async def execute_one(self, sql: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Execute query and return first row as dict (non-blocking)."""
        return await self._pool.fetch_one(sql, params or {})

    async def fetch_all(self, sql: str, params: Optional[Dict] = None) -> List[Dict]:
        """Fetch all rows as list of dicts (alias for execute)."""
        return await self.execute(sql, params)

    async def fetch_one(self, sql: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Fetch first row as dict (alias for execute_one)."""
        return await self.execute_one(sql, params)

    @property
    def stats(self) -> dict:
        """Return pool statistics."""
        return self._pool.stats


async def get_async_db() -> AsyncDatabaseService:
    """FastAPI dependency for async database access.

    Usage in route handlers:
        @router.get("/example")
        async def example(db: AsyncDatabaseService = Depends(get_async_db)):
            rows = await db.execute("SELECT * FROM ...")
            return rows
    """
    return AsyncDatabaseService.get_instance()
