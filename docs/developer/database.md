# Database

GatheRing uses PostgreSQL with pgvector for vector similarity search.

## pycopg - Database Layer

GatheRing uses [pycopg](../../pycopg/README.md), a high-level Python API for PostgreSQL/PostGIS/TimescaleDB. It wraps `asyncpg` (async) and `psycopg2` (sync) with a unified, pythonic interface.

```python
from pycopg import Database, AsyncDatabase

# Sync usage
db = Database.from_env()
db.list_schemas()
db.list_tables("agent")

# Async usage (recommended for API)
db = AsyncDatabase.from_env()
schemas = await db.list_schemas()
users = await db.execute("SELECT * FROM agent.agents WHERE status = %s", ["active"])

# Connection pooling
from pycopg import PooledDatabase

db = PooledDatabase.from_env(min_size=5, max_size=20)
with db.connection() as conn:
    result = conn.execute("SELECT * FROM agent.agents")

# Migrations
from pycopg import Migrator

migrator = Migrator(db, "gathering/db/migrations/")
migrator.migrate()
```

See [pycopg README](../../pycopg/README.md) for full API documentation.

## Async Database Service (v1.0)

For async route handlers, GatheRing provides `AsyncDatabaseService` with connection pooling:

```python
from gathering.db.async_database import AsyncDatabaseService

# Created during FastAPI lifespan startup
async_db = AsyncDatabaseService(database_url)
await async_db.initialize()  # Creates pool (min_size=4, max_size=20)

# Usage in route handlers
async with async_db.connection() as conn:
    result = await conn.execute(
        "SELECT * FROM agent.agents WHERE id = %s", [agent_id]
    )

# Shutdown (last in lifespan teardown)
await async_db.shutdown()
```

The sync `DatabaseService` is preserved for CLI tools and migrations. Async route handlers should use `AsyncDatabaseService` for non-blocking DB access.

### Lifespan Ordering

```text
Startup:  configure_logging -> async DB pool -> scheduler(async_db) -> rate limiter
Shutdown: set_shutting_down -> LB drain (3s) -> scheduler.stop -> task drain (2s)
          -> executor.shutdown -> async_db.shutdown (LAST)
```

## Advisory Locks (v1.0)

Multi-instance task coordination uses PostgreSQL advisory locks:

```python
# Prevent duplicate task execution across instances
async with async_db.connection() as conn:
    result = await conn.execute(
        "SELECT pg_try_advisory_xact_lock(%s, %s)",
        [namespace, action_id]
    )
    acquired = result[0][0]  # True if lock acquired
```

Lock semantics: transaction-scoped, fail-closed on DB error (skip execution rather than risk duplicate).

## Low-Level Drivers

Under the hood, pycopg uses:

| Driver     | Type  | Usage                                       |
|------------|-------|---------------------------------------------|
| `asyncpg`  | Async | Route handlers via AsyncDatabaseService     |
| `psycopg2` | Sync  | Migrations, CLI tools, blocking operations  |

## Database Diagram

![Database Schema](../_static/database/gathering.svg)

*Full database model available in [gathering.dbm](../_static/database/gathering.dbm) (pgModeler format)*

## Overview

The database is organized into schemas:

| Schema | Purpose |
|--------|---------|
| `public` | Common types, functions, extensions |
| `agent` | Agent definitions and sessions |
| `auth` | Users, token blacklist, audit events (v1.0) |
| `circle` | Circle management |
| `conversation` | Conversations and messages |
| `memory` | Long-term memory and RAG |
| `pipeline` | Pipeline definitions, runs, node runs (v1.0) |
| `project` | Project and task management |
| `schedule` | Scheduled actions with execution history (v1.0) |

## Setup

### Prerequisites

```bash
# Install PostgreSQL 15+
sudo apt install postgresql-15

# Install pgvector
sudo apt install postgresql-15-pgvector
```

### Create Database

```bash
# Create user and database
sudo -u postgres createuser gathering
sudo -u postgres createdb gathering -O gathering

# Set password
sudo -u postgres psql -c "ALTER USER gathering PASSWORD 'your_password';"
```

### Enable Extensions

```sql
-- Connect to database
\c gathering

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### Run Migrations

```bash
python -m gathering.db.migrate
```

Or manually:

```bash
for f in gathering/db/migrations/*.sql; do
  psql -d gathering -f "$f"
done
```

## Schema Details

### Agent Schema

```sql
-- agent.agents
CREATE TABLE agent.agents (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(100),
    provider VARCHAR(50) DEFAULT 'anthropic',  -- openai, anthropic, ollama
    model VARCHAR(100) DEFAULT 'claude-sonnet-4-20250514',
    personality JSONB DEFAULT '{}',
    config JSONB DEFAULT '{}',
    status agent_status DEFAULT 'idle',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- agent.sessions
CREATE TABLE agent.sessions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    agent_id BIGINT REFERENCES agent.agents(id),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    context JSONB DEFAULT '{}'
);
```

### Circle Schema

```sql
-- circle.circles
CREATE TABLE circle.circles (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200),
    description TEXT,
    config JSONB DEFAULT '{}',
    status circle_status DEFAULT 'created',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- circle.memberships
CREATE TABLE circle.memberships (
    circle_id BIGINT REFERENCES circle.circles(id),
    agent_id BIGINT REFERENCES agent.agents(id),
    role VARCHAR(50) DEFAULT 'member',
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (circle_id, agent_id)
);
```

### Memory Schema

```sql
-- memory.memories
CREATE TABLE memory.memories (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scope memory_scope NOT NULL,
    scope_id BIGINT,
    agent_id BIGINT REFERENCES agent.agents(id),
    memory_type memory_type DEFAULT 'fact',
    key VARCHAR(200) NOT NULL,
    value TEXT NOT NULL,
    embedding vector(1536),  -- pgvector
    importance FLOAT DEFAULT 0.5,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Vector similarity index
CREATE INDEX idx_memories_embedding
ON memory.memories USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

## Vector Search

### Creating Embeddings

```python
from gathering.memory import EmbeddingService

service = EmbeddingService()
embedding = await service.create_embedding("Some text to embed")
```

### Similarity Search

```sql
-- Find similar memories
SELECT id, key, value,
       1 - (embedding <=> query_embedding) AS similarity
FROM memory.memories
WHERE embedding IS NOT NULL
  AND agent_id = $1
ORDER BY embedding <=> query_embedding
LIMIT 10;
```

Using the helper function:

```python
from gathering.memory import search_similar_memories

results = await search_similar_memories(
    query="What is the user's name?",
    agent_id=1,
    limit=5,
    threshold=0.7
)
```

## Migrations

### Creating a Migration

Create a new file in `gathering/db/migrations/`:

```sql
-- 010_add_new_feature.sql

-- Add new column
ALTER TABLE agent.agents ADD COLUMN new_field VARCHAR(100);

-- Create new table
CREATE TABLE agent.new_table (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- ...
);

-- Create indexes
CREATE INDEX idx_new_field ON agent.agents(new_field);
```

### Migration Best Practices

1. **Incremental changes**: One feature per migration
2. **Backward compatible**: Don't break existing code
3. **Idempotent**: Safe to run multiple times
4. **Documented**: Comment complex changes

## Connection Pooling

GatheRing uses connection pooling for efficiency:

```python
from gathering.db import DatabasePool

# Get pool
pool = await DatabasePool.get_pool()

# Use connection
async with pool.acquire() as conn:
    result = await conn.fetch("SELECT * FROM agent.agents")
```

### Configuration

```env
# .env
DATABASE_URL=postgresql://user:pass@localhost:5432/gathering
DATABASE_POOL_MIN=5
DATABASE_POOL_MAX=20
```

## Backup and Restore

### Backup

```bash
# Full backup
pg_dump -Fc gathering > backup.dump

# Schema only
pg_dump -s gathering > schema.sql

# Data only
pg_dump -a gathering > data.sql
```

### Restore

```bash
# Restore full backup
pg_restore -d gathering backup.dump

# Restore from SQL
psql -d gathering -f schema.sql
```

## Performance

### Indexes

Key indexes for performance:

```sql
-- Agent queries
CREATE INDEX idx_agents_status ON agent.agents(status);
CREATE INDEX idx_agents_name ON agent.agents(name);

-- Memory search
CREATE INDEX idx_memories_agent ON memory.memories(agent_id);
CREATE INDEX idx_memories_scope ON memory.memories(scope, scope_id);

-- Full-text search
CREATE INDEX idx_memories_value_fts
ON memory.memories USING gin(to_tsvector('english', value));
```

### Query Optimization

```sql
-- Explain analyze for debugging
EXPLAIN ANALYZE
SELECT * FROM memory.memories
WHERE agent_id = 1 AND scope = 'agent';

-- Check index usage
SELECT indexrelname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
WHERE schemaname = 'memory';
```

## Troubleshooting

### Connection Issues

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check logs
sudo tail -f /var/log/postgresql/postgresql-15-main.log

# Test connection
psql -h localhost -U gathering -d gathering -c "SELECT 1"
```

### pgvector Issues

```sql
-- Check extension is installed
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Reinstall if needed
DROP EXTENSION IF EXISTS vector CASCADE;
CREATE EXTENSION vector;
```

### Performance Issues

```sql
-- Check table sizes
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

-- Vacuum and analyze
VACUUM ANALYZE memory.memories;
```

## Related Topics

- [Architecture](architecture.md) - System architecture
- [API](api.md) - API development
- [Testing](testing.md) - Database testing
