#!/usr/bin/env python3
"""
GatheRing Database Setup Script.

Creates the database, schemas, and applies migrations using PicoPG.

Usage:
    # From environment variables
    python -m gathering.db.setup

    # With explicit connection
    python -m gathering.db.setup --host localhost --port 5432 --user postgres

    # Create database only
    python -m gathering.db.setup --create-db-only

    # Reset (drop and recreate)
    python -m gathering.db.setup --reset
"""

import argparse
import sys
from pathlib import Path

# Add picopg to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "picopg"))

try:
    from picopg import Database
except ImportError:
    print("Error: picopg not found. Make sure it's in the project directory.")
    sys.exit(1)


# Schema definitions
SCHEMAS = [
    ("agent", "Agents & Identity"),
    ("circle", "Orchestration (Gathering Circles)"),
    ("project", "Projects"),
    ("communication", "Conversations & Messages"),
    ("memory", "Memory & RAG with pgvector"),
    ("review", "Reviews & Quality Control"),
    ("audit", "Audit & Logs"),
]

# Required extensions
EXTENSIONS = [
    "uuid-ossp",
    "vector",  # pgvector for RAG
]


def create_database(admin_db: Database, db_name: str, owner: str = None) -> bool:
    """Create the gathering database if it doesn't exist."""
    if admin_db.database_exists(db_name):
        print(f"  Database '{db_name}' already exists")
        return False

    print(f"  Creating database '{db_name}'...")
    admin_db.create_database(db_name, owner=owner)
    print(f"  Database '{db_name}' created")
    return True


def drop_database(admin_db: Database, db_name: str) -> bool:
    """Drop the gathering database if it exists."""
    if not admin_db.database_exists(db_name):
        print(f"  Database '{db_name}' doesn't exist")
        return False

    print(f"  Dropping database '{db_name}'...")
    admin_db.drop_database(db_name)
    print(f"  Database '{db_name}' dropped")
    return True


def setup_extensions(db: Database) -> None:
    """Install required PostgreSQL extensions."""
    print("\n2. Installing extensions...")
    for ext in EXTENSIONS:
        try:
            if db.has_extension(ext):
                print(f"  Extension '{ext}' already installed")
            else:
                db.create_extension(ext)
                print(f"  Extension '{ext}' installed")
        except Exception as e:
            if "vector" in ext:
                print(f"  Warning: Could not install '{ext}': {e}")
                print("    pgvector may not be available. RAG features will be limited.")
            else:
                raise


def setup_schemas(db: Database) -> None:
    """Create all GatheRing schemas."""
    print("\n3. Creating schemas...")
    for schema_name, description in SCHEMAS:
        if db.schema_exists(schema_name):
            print(f"  Schema '{schema_name}' already exists")
        else:
            db.create_schema(schema_name)
            # Add comment (escape single quotes in description)
            escaped_desc = description.replace("'", "''")
            db.execute(f"COMMENT ON SCHEMA {schema_name} IS '{escaped_desc}'")
            print(f"  Schema '{schema_name}' created - {description}")


def apply_migrations(db: Database, migrations_dir: Path) -> None:
    """Apply SQL migrations in order."""
    print("\n4. Applying migrations...")

    # Check for migrations table
    if not db.table_exists("migrations", schema="public"):
        db.execute("""
            CREATE TABLE IF NOT EXISTS public.migrations (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                version VARCHAR(50) NOT NULL UNIQUE,
                name VARCHAR(200) NOT NULL,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        print("  Created migrations tracking table")

    # Get applied migrations
    applied = {r["version"] for r in db.execute("SELECT version FROM public.migrations")}

    # Migration files in order
    migration_files = sorted(migrations_dir.glob("*.sql"))

    for migration_file in migration_files:
        version = migration_file.stem.split("_")[0]
        name = migration_file.stem

        if version in applied:
            print(f"  [skip] {name} (already applied)")
            continue

        print(f"  [apply] {name}...")
        sql = migration_file.read_text()

        # Execute migration
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

        # Record migration
        db.execute(
            "INSERT INTO public.migrations (version, name) VALUES (%s, %s)",
            [version, name]
        )
        print(f"  [done] {name}")


def show_summary(db: Database) -> None:
    """Show database summary."""
    print("\n" + "=" * 60)
    print("DATABASE SETUP COMPLETE")
    print("=" * 60)

    print(f"\nDatabase: {db.config.database}")
    print(f"Size: {db.size()}")

    print("\nSchemas:")
    for schema in db.list_schemas():
        tables = db.list_tables(schema)
        print(f"  {schema}: {len(tables)} tables")

    print("\nExtensions:")
    for ext in db.list_extensions():
        print(f"  {ext['extname']} v{ext['extversion']}")

    print("\nMigrations applied:")
    for m in db.execute("SELECT version, name, applied_at FROM public.migrations ORDER BY version"):
        print(f"  {m['version']}: {m['name']}")


def main():
    parser = argparse.ArgumentParser(
        description="GatheRing Database Setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Setup from .env file
  python -m gathering.db.setup

  # Setup with explicit connection
  python -m gathering.db.setup --host localhost --user postgres --password secret

  # Reset database (drop and recreate)
  python -m gathering.db.setup --reset

  # Only create database (no migrations)
  python -m gathering.db.setup --create-db-only
        """
    )

    parser.add_argument("--host", default=None, help="Database host")
    parser.add_argument("--port", type=int, default=None, help="Database port")
    parser.add_argument("--user", default=None, help="Database user")
    parser.add_argument("--password", default=None, help="Database password")
    parser.add_argument("--database", default="gathering", help="Database name (default: gathering)")
    parser.add_argument("--owner", default=None, help="Database owner role")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate database")
    parser.add_argument("--create-db-only", action="store_true", help="Only create database, skip migrations")
    parser.add_argument("--env-file", default=None, help="Path to .env file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    print("=" * 60)
    print("GatheRing Database Setup")
    print("=" * 60)

    # Connect to postgres database first (for admin operations)
    print("\n1. Connecting to PostgreSQL...")

    try:
        if args.host or args.user:
            # Build connection from args
            from picopg.config import Config
            config = Config(
                host=args.host or "localhost",
                port=args.port or 5432,
                database="postgres",
                user=args.user or "postgres",
                password=args.password or "",
            )
            admin_db = Database(config)
        else:
            # From environment
            admin_db = Database.from_env(args.env_file)
            # Switch to postgres database for admin
            admin_db = Database(admin_db.config.with_database("postgres"))

        print(f"  Connected to {admin_db.config.host}:{admin_db.config.port}")

    except Exception as e:
        print(f"  Error connecting to PostgreSQL: {e}")
        sys.exit(1)

    db_name = args.database

    # Reset if requested
    if args.reset:
        print(f"\n  Resetting database '{db_name}'...")
        drop_database(admin_db, db_name)

    # Create database
    create_database(admin_db, db_name, owner=args.owner)

    if args.create_db_only:
        print("\n  Database created. Skipping migrations (--create-db-only)")
        return

    # Connect to the gathering database
    print(f"\n  Connecting to '{db_name}'...")
    if args.host or args.user:
        from picopg.config import Config
        config = Config(
            host=args.host or "localhost",
            port=args.port or 5432,
            database=db_name,
            user=args.user or "postgres",
            password=args.password or "",
        )
        db = Database(config)
    else:
        db = Database.from_env(args.env_file)
        db = Database(db.config.with_database(db_name))

    # Setup extensions
    setup_extensions(db)

    # Setup schemas
    setup_schemas(db)

    # Apply migrations
    migrations_dir = Path(__file__).parent / "migrations"
    if migrations_dir.exists():
        apply_migrations(db, migrations_dir)
    else:
        print(f"\n  Warning: Migrations directory not found: {migrations_dir}")

    # Show summary
    show_summary(db)

    print("\nSetup complete!")


if __name__ == "__main__":
    main()
