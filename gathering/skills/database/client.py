"""
Database Skill for GatheRing.
Provides SQL database operations for agents.
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from gathering.skills.base import BaseSkill, SkillResponse, SkillPermission


class DatabaseSkill(BaseSkill):
    """
    SQL database operations skill.

    Provides tools for:
    - Executing SQL queries (SELECT, INSERT, UPDATE, DELETE)
    - Schema inspection and management
    - Database migrations
    - Query analysis and optimization hints
    - Multiple database support (PostgreSQL, SQLite, MySQL)
    """

    name = "database"
    description = "SQL database operations"
    version = "1.0.0"
    required_permissions = [SkillPermission.READ, SkillPermission.WRITE, SkillPermission.EXECUTE]

    # Safety: SQL keywords that require confirmation
    DESTRUCTIVE_KEYWORDS = ["DROP", "DELETE", "TRUNCATE", "ALTER", "UPDATE"]
    MAX_RESULTS = 1000
    MAX_QUERY_LENGTH = 10000

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.connection_string = config.get("connection_string") if config else None
        self.db_type = config.get("db_type", "postgresql") if config else "postgresql"
        self.read_only = config.get("read_only", False) if config else False
        self._connection = None

    def get_tools_definition(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "db_query",
                "description": "Execute a SQL query (SELECT only in read-only mode)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string", "description": "SQL query to execute"},
                        "params": {
                            "type": "object",
                            "description": "Query parameters for parameterized queries"
                        },
                        "limit": {"type": "integer", "description": "Limit results", "default": 100}
                    },
                    "required": ["sql"]
                }
            },
            {
                "name": "db_execute",
                "description": "Execute a SQL statement (INSERT, UPDATE, DELETE)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string", "description": "SQL statement to execute"},
                        "params": {"type": "object", "description": "Statement parameters"},
                        "returning": {"type": "boolean", "description": "Return affected rows", "default": False}
                    },
                    "required": ["sql"]
                }
            },
            {
                "name": "db_schema",
                "description": "Get database schema information",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "schema": {"type": "string", "description": "Schema name", "default": "public"},
                        "table": {"type": "string", "description": "Specific table name (optional)"},
                        "include_indexes": {"type": "boolean", "description": "Include index info", "default": True}
                    },
                    "required": []
                }
            },
            {
                "name": "db_tables",
                "description": "List all tables in the database",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "schema": {"type": "string", "description": "Schema name", "default": "public"},
                        "include_views": {"type": "boolean", "description": "Include views", "default": True}
                    },
                    "required": []
                }
            },
            {
                "name": "db_describe",
                "description": "Describe a table structure",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "table": {"type": "string", "description": "Table name"},
                        "schema": {"type": "string", "description": "Schema name", "default": "public"}
                    },
                    "required": ["table"]
                }
            },
            {
                "name": "db_explain",
                "description": "Explain query execution plan",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string", "description": "SQL query to explain"},
                        "analyze": {"type": "boolean", "description": "Run EXPLAIN ANALYZE", "default": False}
                    },
                    "required": ["sql"]
                }
            },
            {
                "name": "db_migrate",
                "description": "Create or run a database migration",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["create", "up", "down", "status"],
                            "description": "Migration action"
                        },
                        "name": {"type": "string", "description": "Migration name (for create)"},
                        "migrations_dir": {"type": "string", "description": "Migrations directory", "default": "migrations"}
                    },
                    "required": ["action"]
                }
            },
            {
                "name": "db_backup",
                "description": "Create a database backup (schema or data)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "output_path": {"type": "string", "description": "Output file path"},
                        "schema_only": {"type": "boolean", "description": "Export schema only", "default": False},
                        "tables": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific tables to backup"
                        }
                    },
                    "required": ["output_path"]
                }
            },
        ]

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> SkillResponse:
        """Execute a database tool."""
        self.ensure_initialized()

        start_time = datetime.utcnow()

        try:
            handlers = {
                "db_query": self._db_query,
                "db_execute": self._db_execute,
                "db_schema": self._db_schema,
                "db_tables": self._db_tables,
                "db_describe": self._db_describe,
                "db_explain": self._db_explain,
                "db_migrate": self._db_migrate,
                "db_backup": self._db_backup,
            }

            if tool_name not in handlers:
                return SkillResponse(
                    success=False,
                    message=f"Unknown tool: {tool_name}",
                    error="unknown_tool",
                    skill_name=self.name,
                    tool_name=tool_name,
                )

            result = handlers[tool_name](tool_input)
            result.skill_name = self.name
            result.tool_name = tool_name
            result.duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return result

        except Exception as e:
            return SkillResponse(
                success=False,
                message=f"Error executing {tool_name}: {str(e)}",
                error=str(e),
                skill_name=self.name,
                tool_name=tool_name,
            )

    def _check_connection(self) -> Optional[SkillResponse]:
        """Check if database connection is configured."""
        if not self.connection_string:
            return SkillResponse(
                success=False,
                message="No database connection configured",
                error="no_connection",
                data={"hint": "Set connection_string in skill config"}
            )
        return None

    def _is_destructive(self, sql: str) -> bool:
        """Check if SQL is destructive."""
        sql_upper = sql.upper().strip()
        return any(kw in sql_upper for kw in self.DESTRUCTIVE_KEYWORDS)

    def _validate_sql(self, sql: str) -> Optional[SkillResponse]:
        """Validate SQL query."""
        if len(sql) > self.MAX_QUERY_LENGTH:
            return SkillResponse(
                success=False,
                message=f"Query too long: {len(sql)} chars (max {self.MAX_QUERY_LENGTH})",
                error="query_too_long"
            )

        # Basic SQL injection prevention (parameterized queries are still recommended)
        dangerous_patterns = [
            r";\s*DROP\s+",
            r";\s*DELETE\s+",
            r"--\s*$",
            r"/\*.*\*/",
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, sql, re.IGNORECASE):
                return SkillResponse(
                    success=False,
                    message="Potentially dangerous SQL detected",
                    error="dangerous_sql",
                    data={"hint": "Use parameterized queries for user input"}
                )
        return None

    def _db_query(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Execute SELECT query."""
        conn_error = self._check_connection()
        if conn_error:
            return conn_error

        sql = tool_input["sql"].strip()
        params = tool_input.get("params", {})
        limit = min(tool_input.get("limit", 100), self.MAX_RESULTS)

        # Validate
        validation_error = self._validate_sql(sql)
        if validation_error:
            return validation_error

        # In read-only mode, only allow SELECT
        sql_upper = sql.upper()
        if self.read_only and not sql_upper.startswith("SELECT"):
            return SkillResponse(
                success=False,
                message="Only SELECT queries allowed in read-only mode",
                error="read_only_mode"
            )

        # For non-SELECT in query mode, redirect to execute
        if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
            return SkillResponse(
                success=False,
                message="Use db_execute for non-SELECT statements",
                error="use_execute",
                data={"sql": sql}
            )

        # Add LIMIT if not present
        if "LIMIT" not in sql_upper:
            sql = f"{sql} LIMIT {limit}"

        # Execute query (simulated - actual implementation needs DB driver)
        # In production, this would use psycopg2, sqlite3, etc.
        return SkillResponse(
            success=True,
            message="Query ready for execution",
            needs_confirmation=False,
            data={
                "sql": sql,
                "params": params,
                "db_type": self.db_type,
                "note": "Connect to database to execute",
                "example_code": self._generate_query_code(sql, params),
            }
        )

    def _db_execute(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Execute INSERT/UPDATE/DELETE."""
        conn_error = self._check_connection()
        if conn_error:
            return conn_error

        sql = tool_input["sql"].strip()
        params = tool_input.get("params", {})
        returning = tool_input.get("returning", False)

        if self.read_only:
            return SkillResponse(
                success=False,
                message="Database is in read-only mode",
                error="read_only_mode"
            )

        validation_error = self._validate_sql(sql)
        if validation_error:
            return validation_error

        # Require confirmation for destructive operations
        if self._is_destructive(sql):
            return SkillResponse(
                success=True,
                message="Destructive operation requires confirmation",
                needs_confirmation=True,
                confirmation_type="destructive",
                confirmation_message=f"Execute this SQL?\n\n{sql[:500]}{'...' if len(sql) > 500 else ''}",
                data={
                    "sql": sql,
                    "params": params,
                    "returning": returning,
                }
            )

        return SkillResponse(
            success=True,
            message="Statement ready for execution",
            data={
                "sql": sql,
                "params": params,
                "returning": returning,
                "example_code": self._generate_execute_code(sql, params, returning),
            }
        )

    def _db_schema(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Get database schema."""
        schema = tool_input.get("schema", "public")
        table = tool_input.get("table")
        # include_indexes could be used for extended schema info
        _ = tool_input.get("include_indexes", True)

        # Generate schema query based on db type
        if self.db_type == "postgresql":
            if table:
                sql = f"""
                SELECT
                    c.column_name,
                    c.data_type,
                    c.is_nullable,
                    c.column_default,
                    c.character_maximum_length
                FROM information_schema.columns c
                WHERE c.table_schema = '{schema}'
                AND c.table_name = '{table}'
                ORDER BY c.ordinal_position;
                """
            else:
                sql = f"""
                SELECT
                    t.table_name,
                    t.table_type
                FROM information_schema.tables t
                WHERE t.table_schema = '{schema}'
                ORDER BY t.table_name;
                """
        elif self.db_type == "sqlite":
            if table:
                sql = f"PRAGMA table_info({table});"
            else:
                sql = "SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view');"
        else:
            sql = "SHOW TABLES;"  # MySQL

        return SkillResponse(
            success=True,
            message=f"Schema query for {self.db_type}",
            data={
                "sql": sql,
                "schema": schema,
                "table": table,
                "db_type": self.db_type,
            }
        )

    def _db_tables(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """List database tables."""
        schema = tool_input.get("schema", "public")
        include_views = tool_input.get("include_views", True)

        if self.db_type == "postgresql":
            types = "('BASE TABLE', 'VIEW')" if include_views else "('BASE TABLE')"
            sql = f"""
            SELECT
                table_name,
                table_type,
                (SELECT COUNT(*) FROM information_schema.columns
                 WHERE table_schema = t.table_schema AND table_name = t.table_name) as column_count
            FROM information_schema.tables t
            WHERE table_schema = '{schema}'
            AND table_type IN {types}
            ORDER BY table_name;
            """
        elif self.db_type == "sqlite":
            types = "('table', 'view')" if include_views else "('table')"
            sql = f"SELECT name, type FROM sqlite_master WHERE type IN {types} ORDER BY name;"
        else:
            sql = "SHOW FULL TABLES;"

        return SkillResponse(
            success=True,
            message="Tables query ready",
            data={
                "sql": sql,
                "schema": schema,
                "include_views": include_views,
            }
        )

    def _db_describe(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Describe table structure."""
        table = tool_input["table"]
        schema = tool_input.get("schema", "public")

        if self.db_type == "postgresql":
            sql = f"""
            SELECT
                c.column_name as "Column",
                c.data_type as "Type",
                c.is_nullable as "Nullable",
                c.column_default as "Default",
                CASE WHEN pk.column_name IS NOT NULL THEN 'PK' ELSE '' END as "Key",
                CASE WHEN fk.column_name IS NOT NULL THEN 'FK -> ' || fk.foreign_table_name || '.' || fk.foreign_column_name ELSE '' END as "References"
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT ku.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage ku ON tc.constraint_name = ku.constraint_name
                WHERE tc.table_schema = '{schema}' AND tc.table_name = '{table}' AND tc.constraint_type = 'PRIMARY KEY'
            ) pk ON c.column_name = pk.column_name
            LEFT JOIN (
                SELECT
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
                WHERE tc.table_schema = '{schema}' AND tc.table_name = '{table}' AND tc.constraint_type = 'FOREIGN KEY'
            ) fk ON c.column_name = fk.column_name
            WHERE c.table_schema = '{schema}' AND c.table_name = '{table}'
            ORDER BY c.ordinal_position;
            """
        elif self.db_type == "sqlite":
            sql = f"PRAGMA table_info({table});"
        else:
            sql = f"DESCRIBE {table};"

        return SkillResponse(
            success=True,
            message=f"Describe query for {table}",
            data={
                "sql": sql,
                "table": table,
                "schema": schema,
            }
        )

    def _db_explain(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Explain query execution plan."""
        sql = tool_input["sql"]
        analyze = tool_input.get("analyze", False)

        validation_error = self._validate_sql(sql)
        if validation_error:
            return validation_error

        if self.db_type == "postgresql":
            explain_sql = f"EXPLAIN {'ANALYZE ' if analyze else ''}(FORMAT JSON) {sql}"
        elif self.db_type == "sqlite":
            explain_sql = f"EXPLAIN QUERY PLAN {sql}"
        else:
            explain_sql = f"EXPLAIN {'ANALYZE ' if analyze else ''}{sql}"

        if analyze:
            return SkillResponse(
                success=True,
                message="EXPLAIN ANALYZE requires confirmation (executes query)",
                needs_confirmation=True,
                confirmation_type="execute",
                confirmation_message="Run EXPLAIN ANALYZE? This will execute the query.",
                data={
                    "sql": explain_sql,
                    "original_sql": sql,
                    "analyze": analyze,
                }
            )

        return SkillResponse(
            success=True,
            message="Explain query ready",
            data={
                "sql": explain_sql,
                "original_sql": sql,
                "analyze": analyze,
            }
        )

    def _db_migrate(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Database migration operations."""
        action = tool_input["action"]
        name = tool_input.get("name")
        migrations_dir = tool_input.get("migrations_dir", "migrations")

        migrations_path = Path(migrations_dir)

        if action == "create":
            if not name:
                return SkillResponse(
                    success=False,
                    message="Migration name required for create",
                    error="missing_name"
                )

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            migration_name = f"{timestamp}_{name}"

            up_content = f"""-- Migration: {migration_name}
-- Created: {datetime.now().isoformat()}

-- Add your UP migration SQL here
"""

            down_content = f"""-- Migration: {migration_name} (rollback)
-- Created: {datetime.now().isoformat()}

-- Add your DOWN migration SQL here
"""

            return SkillResponse(
                success=True,
                message=f"Migration template created: {migration_name}",
                needs_confirmation=True,
                confirmation_type="write_file",
                confirmation_message=f"Create migration files in {migrations_dir}?",
                data={
                    "migration_name": migration_name,
                    "up_file": str(migrations_path / f"{migration_name}_up.sql"),
                    "down_file": str(migrations_path / f"{migration_name}_down.sql"),
                    "up_content": up_content,
                    "down_content": down_content,
                }
            )

        elif action == "status":
            # List migrations and their status
            if not migrations_path.exists():
                return SkillResponse(
                    success=True,
                    message="No migrations directory found",
                    data={"migrations": [], "migrations_dir": str(migrations_path)}
                )

            migrations = []
            for f in sorted(migrations_path.glob("*_up.sql")):
                name = f.stem.replace("_up", "")
                migrations.append({
                    "name": name,
                    "up_file": str(f),
                    "down_file": str(f.parent / f"{name}_down.sql"),
                })

            return SkillResponse(
                success=True,
                message=f"Found {len(migrations)} migrations",
                data={
                    "migrations": migrations,
                    "migrations_dir": str(migrations_path),
                }
            )

        elif action in ("up", "down"):
            return SkillResponse(
                success=True,
                message=f"Migration {action} requires confirmation",
                needs_confirmation=True,
                confirmation_type="destructive",
                confirmation_message=f"Run migration {action}? This will modify the database.",
                data={
                    "action": action,
                    "migrations_dir": str(migrations_path),
                }
            )

        return SkillResponse(
            success=False,
            message=f"Unknown migration action: {action}",
            error="unknown_action"
        )

    def _db_backup(self, tool_input: Dict[str, Any]) -> SkillResponse:
        """Create database backup."""
        output_path = tool_input["output_path"]
        schema_only = tool_input.get("schema_only", False)
        tables = tool_input.get("tables", [])

        if self.db_type == "postgresql":
            cmd = ["pg_dump"]
            if schema_only:
                cmd.append("--schema-only")
            if tables:
                for table in tables:
                    cmd.extend(["-t", table])
            cmd.extend(["-f", output_path])
            cmd.append(self.connection_string or "DATABASE_URL")
        elif self.db_type == "sqlite":
            cmd = ["sqlite3", self.connection_string or "database.db", f".dump > {output_path}"]
        else:
            cmd = ["mysqldump"]
            if schema_only:
                cmd.append("--no-data")
            cmd.extend(["-r", output_path])

        return SkillResponse(
            success=True,
            message="Backup command ready",
            needs_confirmation=True,
            confirmation_type="execute",
            confirmation_message=f"Create backup at {output_path}?",
            data={
                "command": " ".join(cmd),
                "output_path": output_path,
                "schema_only": schema_only,
                "tables": tables,
            }
        )

    def _generate_query_code(self, sql: str, params: Dict) -> str:
        """Generate example code for query execution."""
        if self.db_type == "postgresql":
            return f"""
import psycopg2

conn = psycopg2.connect(connection_string)
cur = conn.cursor()
cur.execute('''{sql}''', {params})
results = cur.fetchall()
"""
        elif self.db_type == "sqlite":
            return f"""
import sqlite3

conn = sqlite3.connect(database_path)
cur = conn.cursor()
cur.execute('''{sql}''', {params})
results = cur.fetchall()
"""
        return f"-- Execute: {sql}"

    def _generate_execute_code(self, sql: str, params: Dict, returning: bool) -> str:
        """Generate example code for statement execution."""
        fetch = "\nresult = cur.fetchone()" if returning else ""
        return f"""
cur.execute('''{sql}''', {params}){fetch}
conn.commit()
"""
