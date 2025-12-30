"""
GatheRing Database Migrations.

Migration files for creating and updating the database schema.

Schemas:
    - agent: Agents & Identity
    - circle: Orchestration (Gathering Circles)
    - project: Projects
    - communication: Conversations & Messages
    - memory: Memory & RAG (pgvector)
    - review: Reviews & Quality Control
    - audit: Audit & Logs

Usage:
    # Apply all migrations
    python -m gathering.db.migrations

    # Or use the apply function
    from gathering.db.migrations import apply_migrations
    apply_migrations()
"""

import os
from pathlib import Path
from typing import List, Optional

# Migration files in order
MIGRATION_ORDER = [
    "001_init_schemas.sql",
    "002_agent_schema.sql",
    "003_circle_schema.sql",
    "004_project_schema.sql",
    "005_communication_schema.sql",
    "006_memory_schema.sql",
    "007_review_schema.sql",
    "008_audit_schema.sql",
    "009_cross_schema_fks.sql",
]


def get_migrations_dir() -> Path:
    """Get the migrations directory path."""
    return Path(__file__).parent


def get_migration_files() -> List[Path]:
    """Get list of migration files in order."""
    migrations_dir = get_migrations_dir()
    return [migrations_dir / f for f in MIGRATION_ORDER if (migrations_dir / f).exists()]


def read_migration(filename: str) -> str:
    """Read a migration file content."""
    path = get_migrations_dir() / filename
    return path.read_text()


def apply_migrations(
    connection_string: Optional[str] = None,
    verbose: bool = True,
) -> None:
    """
    Apply all migrations to the database.

    Args:
        connection_string: PostgreSQL connection URL. If None, reads from env.
        verbose: Print progress messages.
    """
    import psycopg

    # Get connection string from env if not provided
    if connection_string is None:
        connection_string = (
            os.getenv("GATHERING_DATABASE_URL")
            or os.getenv("DATABASE_URL")
            or "postgresql://postgres@localhost:5432/gathering"
        )

    if verbose:
        print(f"Connecting to database...")

    with psycopg.connect(connection_string) as conn:
        # Check which migrations have been applied
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT version FROM public.migrations")
                applied = {row[0] for row in cur.fetchall()}
        except psycopg.errors.UndefinedTable:
            applied = set()
            conn.rollback()

        for filename in MIGRATION_ORDER:
            version = filename.split("_")[0]

            if version in applied:
                if verbose:
                    print(f"  [skip] {filename} (already applied)")
                continue

            if verbose:
                print(f"  [apply] {filename}...")

            sql = read_migration(filename)

            with conn.cursor() as cur:
                cur.execute(sql)

            conn.commit()

            if verbose:
                print(f"  [done] {filename}")

    if verbose:
        print("All migrations applied successfully.")


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Apply GatheRing database migrations")
    parser.add_argument(
        "--connection-string", "-c",
        help="PostgreSQL connection URL",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress output",
    )

    args = parser.parse_args()

    apply_migrations(
        connection_string=args.connection_string,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
