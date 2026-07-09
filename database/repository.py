"""Repository functions for DuckDB persistence and reads."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

import duckdb
import pandas as pd

from database.schema import EMPLOYEES_TABLE, TELEMETRY_EVENTS_TABLE


EMPLOYEE_COLUMNS = (
    "email",
    "full_name",
    "practice",
    "level",
    "location",
)

TELEMETRY_EVENT_COLUMNS = (
    "event_id",
    "source_file",
    "line_number",
    "event_index",
    "message_type",
    "owner",
    "log_group",
    "log_stream",
    "subscription_filters",
    "year",
    "month",
    "day",
    "outer_timestamp_ms",
    "raw_message",
    "body",
    "scope_name",
    "scope_version",
    "event_timestamp",
    "event_date",
    "event_name",
    "organization_id",
    "session_id",
    "terminal_type",
    "user_account_uuid",
    "user_email",
    "user_id",
    "prompt",
    "prompt_length",
    "prompt_redacted",
    "model",
    "cost_usd",
    "duration_ms",
    "input_tokens",
    "output_tokens",
    "cache_creation_tokens",
    "cache_read_tokens",
    "decision",
    "source",
    "tool_name",
    "decision_source",
    "decision_type",
    "success",
    "tool_result_size_bytes",
    "status_code",
    "error",
    "attempt",
    "host_arch",
    "host_name",
    "os_type",
    "os_version",
    "service_name",
    "service_version",
    "resource_user_email",
    "resource_user_practice",
    "resource_user_profile",
    "resource_user_serial",
    "attributes_json",
    "resource_json",
    "raw_message_json",
    "is_malformed",
    "parse_error",
)

JSON_COLUMNS = (
    "subscription_filters",
    "attributes_json",
    "resource_json",
    "raw_message_json",
)


def save_employees(
    connection: duckdb.DuckDBPyConnection,
    employees: pd.DataFrame,
    *,
    replace: bool = True,
) -> int:
    """Save cleaned employee rows into DuckDB.

    Args:
        connection: Open DuckDB connection.
        employees: Cleaned employee DataFrame.
        replace: If true, existing employee rows are deleted before insert.

    Returns:
        Number of rows inserted.
    """
    prepared = _prepare_dataframe(employees, EMPLOYEE_COLUMNS)
    return _replace_or_append(connection, EMPLOYEES_TABLE, prepared, replace=replace)


def save_telemetry_events(
    connection: duckdb.DuckDBPyConnection,
    telemetry_events: pd.DataFrame,
    *,
    replace: bool = True,
) -> int:
    """Save cleaned telemetry event rows into DuckDB.

    Args:
        connection: Open DuckDB connection.
        telemetry_events: Cleaned flattened telemetry DataFrame.
        replace: If true, existing telemetry rows are deleted before insert.

    Returns:
        Number of rows inserted.
    """
    prepared = _prepare_dataframe(telemetry_events, TELEMETRY_EVENT_COLUMNS)
    prepared = _serialize_json_columns(prepared, JSON_COLUMNS)
    return _replace_or_append(connection, TELEMETRY_EVENTS_TABLE, prepared, replace=replace)


def read_employees(
    connection: duckdb.DuckDBPyConnection,
    *,
    practice: str | None = None,
    location: str | None = None,
) -> pd.DataFrame:
    """Read employees with optional dimensional filters."""
    sql = "SELECT * FROM employees"
    clauses: list[str] = []
    params: list[Any] = []

    if practice is not None:
        clauses.append("practice = ?")
        params.append(practice)
    if location is not None:
        clauses.append("location = ?")
        params.append(location)

    return _read_with_filters(connection, sql, clauses, params)


def read_telemetry_events(
    connection: duckdb.DuckDBPyConnection,
    *,
    event_name: str | None = None,
    user_email: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read telemetry events with optional filters for analytics callers."""
    sql = "SELECT * FROM telemetry_events"
    clauses: list[str] = []
    params: list[Any] = []

    if event_name is not None:
        clauses.append("event_name = ?")
        params.append(event_name)
    if user_email is not None:
        clauses.append("user_email = ?")
        params.append(user_email)
    if start_date is not None:
        clauses.append("event_timestamp >= CAST(? AS TIMESTAMPTZ)")
        params.append(start_date)
    if end_date is not None:
        clauses.append("event_timestamp < CAST(? AS TIMESTAMPTZ)")
        params.append(end_date)

    if limit is not None and limit <= 0:
        raise ValueError("limit must be a positive integer")

    query = _build_filtered_query(sql, clauses)
    query += " ORDER BY event_timestamp"
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    return connection.execute(query, params).fetchdf()


def read_enriched_telemetry_events(
    connection: duckdb.DuckDBPyConnection,
    *,
    event_name: str | None = None,
    practice: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Read telemetry events joined to employee dimensions."""
    sql = """
        SELECT
            t.*,
            e.full_name,
            e.practice,
            e.level,
            e.location
        FROM telemetry_events AS t
        LEFT JOIN employees AS e
            ON t.user_email = e.email
    """
    clauses: list[str] = []
    params: list[Any] = []

    if event_name is not None:
        clauses.append("t.event_name = ?")
        params.append(event_name)
    if practice is not None:
        clauses.append("e.practice = ?")
        params.append(practice)
    if start_date is not None:
        clauses.append("t.event_timestamp >= CAST(? AS TIMESTAMPTZ)")
        params.append(start_date)
    if end_date is not None:
        clauses.append("t.event_timestamp < CAST(? AS TIMESTAMPTZ)")
        params.append(end_date)

    if limit is not None and limit <= 0:
        raise ValueError("limit must be a positive integer")

    query = _build_filtered_query(sql, clauses)
    query += " ORDER BY t.event_timestamp"
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    return connection.execute(query, params).fetchdf()


def count_rows(connection: duckdb.DuckDBPyConnection, table_name: str) -> int:
    """Return a row count for a known repository table."""
    if table_name not in {EMPLOYEES_TABLE, TELEMETRY_EVENTS_TABLE}:
        raise ValueError(f"Unsupported table name: {table_name}")
    result = connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
    return int(result[0]) if result else 0


def _replace_or_append(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
    dataframe: pd.DataFrame,
    *,
    replace: bool,
) -> int:
    """Insert a DataFrame into a known table."""
    if dataframe.empty:
        return 0

    temp_name = f"tmp_{table_name}"
    connection.register(temp_name, dataframe)
    try:
        connection.execute("BEGIN TRANSACTION")
        if replace:
            connection.execute(f"DELETE FROM {table_name}")
        connection.execute(_insert_sql(table_name, dataframe.columns))
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    finally:
        connection.unregister(temp_name)

    return len(dataframe)


def _prepare_dataframe(
    dataframe: pd.DataFrame,
    columns: Sequence[str],
) -> pd.DataFrame:
    """Return a copy containing every schema column in schema order."""
    prepared = dataframe.copy()
    for column in columns:
        if column not in prepared.columns:
            prepared[column] = pd.NA
    return prepared.loc[:, list(columns)]


def _serialize_json_columns(
    dataframe: pd.DataFrame,
    columns: Sequence[str],
) -> pd.DataFrame:
    """Serialize Python objects into JSON strings for DuckDB JSON columns."""
    serialized = dataframe.copy()
    for column in columns:
        if column in serialized.columns:
            serialized[column] = serialized[column].map(_to_json_string)
    return serialized


def _to_json_string(value: Any) -> str | None:
    """Convert Python values to JSON strings while preserving nulls."""
    if value is None or value is pd.NA:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, default=str)


def _insert_sql(table_name: str, columns: Sequence[str]) -> str:
    """Build an INSERT statement for a registered temp DataFrame."""
    column_sql = ", ".join(columns)
    select_sql = ", ".join(_select_expression(column) for column in columns)
    return f"INSERT INTO {table_name} ({column_sql}) SELECT {select_sql} FROM tmp_{table_name}"


def _select_expression(column: str) -> str:
    """Return the select expression needed for a column insert."""
    if column in JSON_COLUMNS:
        return f"CAST({column} AS JSON) AS {column}"
    return column


def _read_with_filters(
    connection: duckdb.DuckDBPyConnection,
    base_sql: str,
    clauses: Sequence[str],
    params: Sequence[Any],
) -> pd.DataFrame:
    """Execute a SELECT query with optional WHERE clauses."""
    query = _build_filtered_query(base_sql, clauses)
    return connection.execute(query, params).fetchdf()


def _build_filtered_query(base_sql: str, clauses: Sequence[str]) -> str:
    """Append WHERE clauses to a SELECT statement."""
    if not clauses:
        return base_sql
    return f"{base_sql} WHERE {' AND '.join(clauses)}"
