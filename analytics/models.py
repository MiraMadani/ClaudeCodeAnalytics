"""Model, token, and practice cost analytics."""

from __future__ import annotations

import duckdb
import pandas as pd

from analytics._filters import employee_join, event_filters, where_sql


def requests_per_model(
    connection: duckdb.DuckDBPyConnection,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    practice: str | None = None,
    model: str | None = None,
) -> pd.DataFrame:
    """Return API request counts by model.

    Business value: shows model adoption mix and helps explain cost patterns.
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
            t.model,
            COUNT(*) AS request_count,
            COALESCE(SUM(t.cost_usd), 0) AS cost_usd,
            COALESCE(AVG(t.duration_ms), 0) AS average_duration_ms
        FROM telemetry_events AS t
        {employee_join("t")}
        {where_sql(clauses + ["t.model IS NOT NULL"])}
        GROUP BY t.model
        ORDER BY request_count DESC, t.model
        """,
        params,
    ).fetchdf()


def token_usage_per_model(
    connection: duckdb.DuckDBPyConnection,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    practice: str | None = None,
    model: str | None = None,
) -> pd.DataFrame:
    """Return token usage by model.

    Business value: reveals which models are driving workload volume, including
    cache activity that may not be obvious from request counts alone.
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
            t.model,
            COALESCE(SUM(t.input_tokens), 0) AS input_tokens,
            COALESCE(SUM(t.output_tokens), 0) AS output_tokens,
            COALESCE(SUM(t.cache_creation_tokens), 0) AS cache_creation_tokens,
            COALESCE(SUM(t.cache_read_tokens), 0) AS cache_read_tokens,
            COALESCE(SUM(
                COALESCE(t.input_tokens, 0)
                + COALESCE(t.output_tokens, 0)
                + COALESCE(t.cache_creation_tokens, 0)
                + COALESCE(t.cache_read_tokens, 0)
            ), 0) AS total_tokens
        FROM telemetry_events AS t
        {employee_join("t")}
        {where_sql(clauses + ["t.model IS NOT NULL"])}
        GROUP BY t.model
        ORDER BY total_tokens DESC, t.model
        """,
        params,
    ).fetchdf()


def cost_per_practice(
    connection: duckdb.DuckDBPyConnection,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    practice: str | None = None,
    model: str | None = None,
) -> pd.DataFrame:
    """Return API cost by employee practice.

    Business value: allocates AI spend to organizational groups for budgeting
    and adoption planning.
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
            COALESCE(e.practice, t.resource_user_practice, 'Unknown') AS practice,
            COUNT(*) AS request_count,
            COUNT(DISTINCT t.user_email) AS active_users,
            COALESCE(SUM(t.cost_usd), 0) AS cost_usd,
            CASE
                WHEN COUNT(DISTINCT t.user_email) = 0 THEN 0
                ELSE COALESCE(SUM(t.cost_usd), 0)
                    / COUNT(DISTINCT t.user_email)
            END AS cost_per_active_user
        FROM telemetry_events AS t
        {employee_join("t")}
        {where_sql(clauses)}
        GROUP BY COALESCE(e.practice, t.resource_user_practice, 'Unknown')
        ORDER BY cost_usd DESC, practice
        """,
        params,
    ).fetchdf()


def average_tokens_per_model_request(connection: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Return average token volume per request by model.

    Business value: compares request size across models so cost and latency can
    be interpreted against workload shape.
    """
    return connection.execute(
        """
        SELECT
            model,
            COUNT(*) AS request_count,
            COALESCE(AVG(
                COALESCE(input_tokens, 0)
                + COALESCE(output_tokens, 0)
                + COALESCE(cache_creation_tokens, 0)
                + COALESCE(cache_read_tokens, 0)
            ), 0) AS average_tokens_per_request
        FROM telemetry_events
        WHERE event_name = 'api_request'
            AND model IS NOT NULL
        GROUP BY model
        ORDER BY average_tokens_per_request DESC, model
        """
    ).fetchdf()
