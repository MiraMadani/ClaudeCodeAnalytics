"""Core KPI queries for Claude Code telemetry analytics."""

from __future__ import annotations

import duckdb
import pandas as pd

from analytics._filters import employee_join, event_filters, where_sql


def total_users(connection: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Return the number of unique telemetry users.

    Business value: shows adoption breadth across the organization.
    """
    return connection.execute(
        """
        SELECT COUNT(DISTINCT user_email) AS total_users
        FROM telemetry_events
        WHERE user_email IS NOT NULL
        """
    ).fetchdf()


def total_sessions(connection: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Return the number of unique telemetry sessions.

    Business value: measures how often people start meaningful work sessions.
    """
    return connection.execute(
        """
        SELECT COUNT(DISTINCT session_id) AS total_sessions
        FROM telemetry_events
        WHERE session_id IS NOT NULL
        """
    ).fetchdf()


def total_events(connection: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Return the total number of telemetry events.

    Business value: provides the broadest volume indicator for platform usage.
    """
    return connection.execute(
        """
        SELECT COUNT(*) AS total_events
        FROM telemetry_events
        """
    ).fetchdf()


def total_token_usage(connection: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Return total API token usage.

    Business value: quantifies model workload and helps explain spend trends.
    """
    return connection.execute(
        """
        SELECT
            COALESCE(SUM(input_tokens), 0) AS input_tokens,
            COALESCE(SUM(output_tokens), 0) AS output_tokens,
            COALESCE(SUM(cache_creation_tokens), 0) AS cache_creation_tokens,
            COALESCE(SUM(cache_read_tokens), 0) AS cache_read_tokens,
            COALESCE(
                SUM(
                    COALESCE(input_tokens, 0)
                    + COALESCE(output_tokens, 0)
                    + COALESCE(cache_creation_tokens, 0)
                    + COALESCE(cache_read_tokens, 0)
                ),
                0
            ) AS total_tokens
        FROM telemetry_events
        WHERE event_name = 'api_request'
        """
    ).fetchdf()


def total_cost(connection: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Return total API cost in USD.

    Business value: gives the headline spend number for budget tracking.
    """
    return connection.execute(
        """
        SELECT COALESCE(SUM(cost_usd), 0) AS total_cost_usd
        FROM telemetry_events
        WHERE event_name = 'api_request'
        """
    ).fetchdf()


def average_session_duration(connection: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Return average session duration in milliseconds.

    Business value: indicates whether users are having short interactions or
    sustained work sessions.
    """
    return connection.execute(
        """
        WITH sessions AS (
            SELECT
                session_id,
                DATE_DIFF(
                    'millisecond',
                    MIN(event_timestamp),
                    MAX(event_timestamp)
                ) AS session_duration_ms
            FROM telemetry_events
            WHERE session_id IS NOT NULL
            GROUP BY session_id
        )
        SELECT
            COALESCE(AVG(session_duration_ms), 0) AS average_session_duration_ms
        FROM sessions
        """
    ).fetchdf()


def success_rate(connection: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Return tool execution success rate.

    Business value: tracks reliability of tool-assisted workflows.
    """
    return connection.execute(
        """
        SELECT
            COUNT(*) AS tool_result_count,
            COALESCE(SUM(CASE WHEN success THEN 1 ELSE 0 END), 0) AS successful_tool_results,
            CASE
                WHEN COUNT(*) = 0 THEN 0
                ELSE COALESCE(SUM(CASE WHEN success THEN 1 ELSE 0 END), 0)::DOUBLE
                    / COUNT(*)
            END AS success_rate
        FROM telemetry_events
        WHERE event_name = 'tool_result'
        """
    ).fetchdf()


def average_tokens_per_request(connection: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Return average token volume per API request.

    Business value: helps identify whether requests are becoming larger and
    more expensive over time.
    """
    return connection.execute(
        """
        SELECT
            COUNT(*) AS api_request_count,
            COALESCE(AVG(
                COALESCE(input_tokens, 0)
                + COALESCE(output_tokens, 0)
                + COALESCE(cache_creation_tokens, 0)
                + COALESCE(cache_read_tokens, 0)
            ), 0) AS average_tokens_per_request
        FROM telemetry_events
        WHERE event_name = 'api_request'
        """
    ).fetchdf()


def kpi_summary(
    connection: duckdb.DuckDBPyConnection,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    practice: str | None = None,
    model: str | None = None,
) -> pd.DataFrame:
    """Return a single-row summary of headline KPIs.

    Business value: supplies metric cards for an executive overview.
    """
    clauses, params = event_filters(
        alias="t",
        start_date=start_date,
        end_date=end_date,
        practice=practice,
        model=model,
        model_by_session=True,
    )
    filtered_events = f"""
        SELECT t.*
        FROM telemetry_events AS t
        {employee_join("t")}
        {where_sql(clauses)}
    """
    return connection.execute(
        f"""
        WITH sessions AS (
            SELECT
                session_id,
                DATE_DIFF('millisecond', MIN(event_timestamp), MAX(event_timestamp))
                    AS session_duration_ms
            FROM ({filtered_events})
            WHERE session_id IS NOT NULL
            GROUP BY session_id
        )
        SELECT
            COUNT(DISTINCT user_email) AS total_users,
            COUNT(DISTINCT session_id) AS total_sessions,
            COUNT(*) AS total_events,
            COALESCE(SUM(CASE WHEN event_name = 'api_request' THEN cost_usd END), 0)
                AS total_cost_usd,
            COALESCE(SUM(
                CASE
                    WHEN event_name = 'api_request' THEN
                        COALESCE(input_tokens, 0)
                        + COALESCE(output_tokens, 0)
                        + COALESCE(cache_creation_tokens, 0)
                        + COALESCE(cache_read_tokens, 0)
                END
            ), 0) AS total_tokens,
            (SELECT COALESCE(AVG(session_duration_ms), 0) FROM sessions)
                AS average_session_duration_ms
        FROM ({filtered_events})
        """,
        params * 2,
    ).fetchdf()


def filter_options(connection: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Return available dashboard filter values.

    Business value: keeps dashboard filters aligned to data that actually
    exists, reducing empty or invalid selections.
    """
    return connection.execute(
        """
        SELECT
            MIN(event_date) AS min_date,
            MAX(event_date) AS max_date,
            LIST(DISTINCT e.practice ORDER BY e.practice)
                FILTER (WHERE e.practice IS NOT NULL) AS practices,
            LIST(DISTINCT model ORDER BY model)
                FILTER (WHERE model IS NOT NULL) AS models
        FROM telemetry_events AS t
        LEFT JOIN employees AS e
            ON t.user_email = e.email
        """
    ).fetchdf()
