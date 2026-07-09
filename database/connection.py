"""DuckDB connection management."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import duckdb

from database.schema import create_schema


DEFAULT_DATABASE_PATH = Path("database/claude_code_analytics.duckdb")
PathLike = str | Path


def connect(
    database_path: PathLike = DEFAULT_DATABASE_PATH,
    *,
    initialize: bool = True,
    read_only: bool = False,
) -> duckdb.DuckDBPyConnection:
    """Create a DuckDB connection and optionally initialize the schema.

    Args:
        database_path: Path to the DuckDB database file. The parent directory
            is created automatically for writable connections.
        initialize: Whether to create required tables if they do not exist.
        read_only: Open the database in read-only mode.

    Returns:
        An open DuckDB connection. The caller is responsible for closing it.
    """
    path = Path(database_path)
    if not read_only:
        path.parent.mkdir(parents=True, exist_ok=True)

    connection = duckdb.connect(str(path), read_only=read_only)
    if initialize and not read_only:
        create_schema(connection)
    return connection


@contextmanager
def managed_connection(
    database_path: PathLike = DEFAULT_DATABASE_PATH,
    *,
    initialize: bool = True,
    read_only: bool = False,
) -> Iterator[duckdb.DuckDBPyConnection]:
    """Yield a DuckDB connection and close it after use."""
    connection = connect(
        database_path=database_path,
        initialize=initialize,
        read_only=read_only,
    )
    try:
        yield connection
    finally:
        connection.close()
