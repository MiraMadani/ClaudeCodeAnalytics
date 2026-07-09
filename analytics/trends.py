"""Time-series analytics queries."""

from __future__ import annotations

import duckdb
import pandas as pd

from analytics._filters import employee_join, event_filters, where_sql


def requests_per_day(
    connection: duckdb.DuckDBPyConnection,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    practice: str | None = None,
    model: str | None = None,
) -> pd.DataFrame:
    """Return API request counts by day.

    Business value: shows demand trends and highlights adoption spikes or drops.
    """
    clauses, params = event_filters(
        alias="t",
        start_date=start_date,
        end_date=end_date,
        practice=practice,
        model=model,
        event_name="api_request",
    )
    return connection.execute(
        f"""
        SELECT
            t.event_date,
            COUNT(*) AS request_count
        FROM telemetry_events AS t
        {employee_join("t")}
        {where_sql(clauses)}
        GROUP BY t.event_date
        ORDER BY t.event_date
        """,
        params,
    ).fetchdf()


def daily_cost(connection: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Return API cost by day.

    Business value: supports budget monitoring and daily anomaly detection.
    """
    return connection.execute(
        """
        SELECT
            event_date,
            COALESCE(SUM(cost_usd), 0) AS cost_usd
        FROM telemetry_events
        WHERE event_name = 'api_request'
        GROUP BY event_date
        ORDER BY event_date
        """
    ).fetchdf()


def daily_active_users(connection: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Return active telemetry users by day.

    Business value: tracks day-to-day adoption independent of event volume.
    """
    return connection.execute(
        """
        SELECT
            event_date,
            COUNT(DISTINCT user_email) AS active_users
        FROM telemetry_events
        WHERE user_email IS NOT NULL
        GROUP BY event_date
        ORDER BY event_date
        """
    ).fetchdf()


def daily_success_rate(connection: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Return tool success rate by day.

    Business value: reveals reliability regressions in developer workflows.
    """
    return connection.execute(
        """
        SELECT
            event_date,
            COUNT(*) AS tool_result_count,
            CASE
                WHEN COUNT(*) = 0 THEN 0
                ELSE SUM(CASE WHEN success THEN 1 ELSE 0 END)::DOUBLE / COUNT(*)
            END AS success_rate
        FROM telemetry_events
        WHERE event_name = 'tool_result'
        GROUP BY event_date
        ORDER BY event_date
        """
    ).fetchdf()
