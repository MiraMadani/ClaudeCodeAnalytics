"""Dash callbacks for the Executive Overview dashboard."""

from __future__ import annotations

from datetime import timedelta

import duckdb
import pandas as pd
from dash import Input, Output

from analytics.metrics import kpi_summary
from analytics.models import cost_per_practice, token_usage_per_model
from analytics.trends import requests_per_day
from analytics.users import top_active_users, top_used_tools
from dashboard.charts import (
    cost_by_practice_chart,
    requests_per_day_chart,
    token_usage_by_model_chart,
    tool_usage_distribution_chart,
    top_active_users_chart,
)


def register_callbacks(app: object, connection: duckdb.DuckDBPyConnection) -> None:
    """Register all dashboard callbacks."""

    @app.callback(
        Output("kpi-total-users", "children"),
        Output("kpi-total-sessions", "children"),
        Output("kpi-total-events", "children"),
        Output("kpi-total-cost", "children"),
        Output("kpi-total-tokens", "children"),
        Output("requests-per-day-chart", "figure"),
        Output("token-usage-by-model-chart", "figure"),
        Output("cost-by-practice-chart", "figure"),
        Output("top-active-users-chart", "figure"),
        Output("tool-usage-distribution-chart", "figure"),
        Input("date-range-filter", "start_date"),
        Input("date-range-filter", "end_date"),
        Input("practice-filter", "value"),
        Input("model-filter", "value"),
    )
    def update_overview(
        start_date: str | None,
        end_date: str | None,
        practice: str | None,
        model: str | None,
    ) -> tuple[object, ...]:
        """Update KPI cards and charts when filters change."""
        end_exclusive = _exclusive_end_date(end_date)
        filters = {
            "start_date": start_date,
            "end_date": end_exclusive,
            "practice": practice,
            "model": model,
        }

        summary = kpi_summary(connection, **filters).iloc[0]
        requests = requests_per_day(connection, **filters)
        tokens = token_usage_per_model(connection, **filters)
        practice_cost = cost_per_practice(connection, **filters)
        users = top_active_users(connection, limit=10, **filters)
        tools = top_used_tools(connection, limit=10, **filters)

        return (
            _format_int(summary["total_users"]),
            _format_int(summary["total_sessions"]),
            _format_int(summary["total_events"]),
            _format_currency(summary["total_cost_usd"]),
            _format_int(summary["total_tokens"]),
            requests_per_day_chart(requests),
            token_usage_by_model_chart(tokens),
            cost_by_practice_chart(practice_cost),
            top_active_users_chart(users),
            tool_usage_distribution_chart(tools),
        )


def _exclusive_end_date(end_date: str | None) -> str | None:
    """Convert an inclusive Dash end date into an exclusive SQL bound."""
    if end_date is None:
        return None
    parsed = pd.to_datetime(end_date)
    return (parsed + timedelta(days=1)).strftime("%Y-%m-%d")


def _format_int(value: object) -> str:
    """Format a numeric KPI as an integer string."""
    return f"{int(value):,}"


def _format_currency(value: object) -> str:
    """Format a numeric KPI as USD."""
    return f"${float(value):,.2f}"
