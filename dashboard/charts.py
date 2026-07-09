"""Plotly figure builders for the dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def requests_per_day_chart(data: pd.DataFrame) -> go.Figure:
    """Build the requests-per-day line chart."""
    if data.empty:
        return _empty_figure("Requests per Day")
    return px.line(
        data,
        x="event_date",
        y="request_count",
        markers=True,
        title="Requests per Day",
        labels={"event_date": "Date", "request_count": "API Requests"},
    )


def token_usage_by_model_chart(data: pd.DataFrame) -> go.Figure:
    """Build the token usage by model bar chart."""
    if data.empty:
        return _empty_figure("Token Usage by Model")
    return px.bar(
        data,
        x="model",
        y="total_tokens",
        title="Token Usage by Model",
        labels={"model": "Model", "total_tokens": "Total Tokens"},
    )


def cost_by_practice_chart(data: pd.DataFrame) -> go.Figure:
    """Build the cost by practice bar chart."""
    if data.empty:
        return _empty_figure("Cost by Practice")
    return px.bar(
        data,
        x="practice",
        y="cost_usd",
        title="Cost by Practice",
        labels={"practice": "Practice", "cost_usd": "Cost USD"},
    )


def top_active_users_chart(data: pd.DataFrame) -> go.Figure:
    """Build the top active users horizontal bar chart."""
    if data.empty:
        return _empty_figure("Top Active Users")
    sorted_data = data.sort_values("event_count", ascending=True)
    return px.bar(
        sorted_data,
        x="event_count",
        y="user_email",
        orientation="h",
        title="Top Active Users",
        labels={"event_count": "Events", "user_email": "User"},
        hover_data=["full_name", "practice", "session_count", "cost_usd"],
    )


def tool_usage_distribution_chart(data: pd.DataFrame) -> go.Figure:
    """Build the tool usage distribution pie chart."""
    if data.empty:
        return _empty_figure("Tool Usage Distribution")
    return px.pie(
        data,
        names="tool_name",
        values="tool_result_count",
        title="Tool Usage Distribution",
    )


def _empty_figure(title: str) -> go.Figure:
    """Return a consistent empty-state figure."""
    figure = go.Figure()
    figure.update_layout(
        title=title,
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[
            {
                "text": "No data for the selected filters",
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {"size": 14},
            }
        ],
    )
    return figure
