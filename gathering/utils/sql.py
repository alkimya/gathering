"""
SQL safety utilities for GatheRing.
Provides helpers to build dynamic SQL safely with column allowlists.
"""

from typing import Any, Optional


def safe_update_builder(
    allowed_columns: set[str],
    updates: dict[str, Any],
    always_set: Optional[dict[str, str]] = None,
) -> tuple[str, dict]:
    """Build a safe SET clause from allowed column names.

    All column names are validated against the allowlist. Values are
    parameterized using %(param)s placeholders (psycopg named params).

    Args:
        allowed_columns: Set of column names allowed in SET clause.
        updates: Dict of {column_name: value} from caller (may include user input keys).
        always_set: Dict of {column_name: raw_sql_expression} always appended
                    (e.g., {"updated_at": "CURRENT_TIMESTAMP"}). These are NOT parameterized.

    Returns:
        Tuple of (SET clause string, params dict).

    Raises:
        ValueError: If any column name is not in the allowlist.

    Example:
        >>> clause, params = safe_update_builder(
        ...     {"name", "description", "status"},
        ...     {"name": "New Name", "status": "active"},
        ...     always_set={"updated_at": "CURRENT_TIMESTAMP"},
        ... )
        >>> clause
        'name = %(name)s, status = %(status)s, updated_at = CURRENT_TIMESTAMP'
    """
    set_parts: list[str] = []
    params: dict[str, Any] = {}

    for col, val in updates.items():
        if col not in allowed_columns:
            raise ValueError(
                f"Column {col!r} not in allowed columns: {sorted(allowed_columns)}"
            )
        set_parts.append(f"{col} = %({col})s")
        params[col] = val

    if always_set:
        for col, expr in always_set.items():
            set_parts.append(f"{col} = {expr}")

    return ", ".join(set_parts), params
