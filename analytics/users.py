"""User and tool activity analytics."""

from __future__ import annotations

import duckdb
import pandas as pd

from analytics._filters import event_filters, where_sql


def top_active_users(
    connection: duckdb.DuckDBPyConnection,
    *,
    limit: int = 10,
    start_date: str | None = None,
    end_date: str | None = None,
    practice: str | None = None,
    model: str | None = None,
) -> pd.DataFrame:
    """Return the most active users by telemetry event count.

    Business value: identifies power users and candidates for workflow study,
    enablement feedback, or cost review.
    """
    _validate_limit(limit)
    clauses, params = event_filters(
        alias="t",
        start_date=start_date,
        end_date=end_date,
        practice=practice,
        model=model,
        model_by_session=True,
    )
    return connection.execute(
        f"""
        SELECT
            t.user_email,
            e.full_name,
            e.practice,
            e.level,
            e.location,
            COUNT(*) AS event_count,
            COUNT(DISTINCT t.session_id) AS session_count,
            SUM(CASE WHEN t.event_name = 'user_prompt' THEN 1 ELSE 0 END)
                AS prompt_count,
            SUM(CASE WHEN t.event_name = 'api_request' THEN 1 ELSE 0 END)
                AS api_request_count,
            COALESCE(SUM(CASE WHEN t.event_name = 'api_request' THEN t.cost_usd END), 0)
                AS cost_usd
        FROM telemetry_events AS t
        LEFT JOIN employees AS e
            ON t.user_email = e.email
        {where_sql(clauses + ["t.user_email IS NOT NULL"])}
        GROUP BY
            t.user_email,
            e.full_name,
            e.practice,
            e.level,
            e.location
        ORDER BY event_count DESC, t.user_email
        LIMIT ?
        """,
        [*params, limit],
    ).fetchdf()


def top_used_tools(
    connection: duckdb.DuckDBPyConnection,
    *,
    limit: int = 10,
    start_date: str | None = None,
    end_date: str | None = None,
    practice: str | None = None,
    model: str | None = None,
) -> pd.DataFrame:
    """Return the most frequently used tools.

    Business value: shows which tools drive the most workflow activity and
    where reliability or UX improvements would have the largest impact.
    """
    _validate_limit(limit)
    clauses, params = event_filters(
        alias="t",
        start_date=start_date,
        end_date=end_date,
        practice=practice,
        model=model,
        event_name="tool_result",
        model_by_session=True,
    )
    return connection.execute(
        f"""
        SELECT
            t.tool_name,
            COUNT(*) AS tool_result_count,
            COALESCE(SUM(CASE WHEN t.success THEN 1 ELSE 0 END), 0)
                AS successful_tool_results,
            CASE
                WHEN COUNT(*) = 0 THEN 0
                ELSE COALESCE(SUM(CASE WHEN t.success THEN 1 ELSE 0 END), 0)::DOUBLE
                    / COUNT(*)
            END AS success_rate,
            COALESCE(AVG(t.duration_ms), 0) AS average_duration_ms
        FROM telemetry_events AS t
        LEFT JOIN employees AS e
            ON t.user_email = e.email
        {where_sql(clauses + ["t.tool_name IS NOT NULL"])}
        GROUP BY t.tool_name
        ORDER BY tool_result_count DESC, t.tool_name
        LIMIT ?
        """,
        [*params, limit],
    ).fetchdf()


def user_activity_summary(connection: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Return activity metrics for every user.

    Business value: provides a user-level table for drilldowns and segmentation.
    """
    return connection.execute(
        """
        SELECT
            t.user_email,
            e.full_name,
            e.practice,
            e.level,
            e.location,
            COUNT(*) AS event_count,
            COUNT(DISTINCT t.session_id) AS session_count,
            SUM(CASE WHEN t.event_name = 'user_prompt' THEN 1 ELSE 0 END)
                AS prompt_count,
            SUM(CASE WHEN t.event_name = 'api_request' THEN 1 ELSE 0 END)
                AS api_request_count,
            SUM(CASE WHEN t.event_name = 'tool_result' THEN 1 ELSE 0 END)
                AS tool_result_count,
            COALESCE(SUM(CASE WHEN t.event_name = 'api_request' THEN t.cost_usd END), 0)
                AS cost_usd
        FROM telemetry_events AS t
        LEFT JOIN employees AS e
            ON t.user_email = e.email
        WHERE t.user_email IS NOT NULL
        GROUP BY
            t.user_email,
            e.full_name,
            e.practice,
            e.level,
            e.location
        ORDER BY event_count DESC, t.user_email
        """
    ).fetchdf()


def _validate_limit(limit: int) -> None:
    """Validate ranking result limits."""
    if limit <= 0:
        raise ValueError("limit must be a positive integer")
