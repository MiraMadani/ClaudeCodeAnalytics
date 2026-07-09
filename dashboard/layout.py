"""Dash layout for the Executive Overview page."""

from __future__ import annotations

from typing import Any

from dash import dcc, html


def create_layout(filter_options: dict[str, Any]) -> html.Div:
    """Create the dashboard layout."""
    return html.Div(
        [
            html.Header(
                [
                    html.H1("Claude Code Analytics"),
                    html.P("Executive Overview"),
                ],
                className="app-header",
            ),
            _filters(filter_options),
            _kpi_cards(),
            html.Div(
                [
                    dcc.Graph(id="requests-per-day-chart"),
                    dcc.Graph(id="token-usage-by-model-chart"),
                    dcc.Graph(id="cost-by-practice-chart"),
                    dcc.Graph(id="top-active-users-chart"),
                    dcc.Graph(id="tool-usage-distribution-chart"),
                ],
                className="chart-grid",
            ),
        ],
        className="app-shell",
    )


def _filters(filter_options: dict[str, Any]) -> html.Section:
    """Create dashboard filters."""
    return html.Section(
        [
            html.Div(
                [
                    html.Label("Date range", htmlFor="date-range-filter"),
                    dcc.DatePickerRange(
                        id="date-range-filter",
                        min_date_allowed=filter_options.get("min_date"),
                        max_date_allowed=filter_options.get("max_date"),
                        start_date=filter_options.get("min_date"),
                        end_date=filter_options.get("max_date"),
                    ),
                ],
                className="filter-control",
            ),
            html.Div(
                [
                    html.Label("Practice", htmlFor="practice-filter"),
                    dcc.Dropdown(
                        id="practice-filter",
                        options=_dropdown_options(filter_options.get("practices", [])),
                        placeholder="All practices",
                        clearable=True,
                    ),
                ],
                className="filter-control",
            ),
            html.Div(
                [
                    html.Label("Model", htmlFor="model-filter"),
                    dcc.Dropdown(
                        id="model-filter",
                        options=_dropdown_options(filter_options.get("models", [])),
                        placeholder="All models",
                        clearable=True,
                    ),
                ],
                className="filter-control",
            ),
        ],
        className="filters",
    )


def _kpi_cards() -> html.Section:
    """Create KPI card placeholders updated by callbacks."""
    cards = [
        ("Total Users", "kpi-total-users"),
        ("Total Sessions", "kpi-total-sessions"),
        ("Total Events", "kpi-total-events"),
        ("Total Cost", "kpi-total-cost"),
        ("Total Tokens", "kpi-total-tokens"),
    ]
    return html.Section(
        [
            html.Div(
                [html.Span(label, className="kpi-label"), html.Strong(id=element_id)],
                className="kpi-card",
            )
            for label, element_id in cards
        ],
        className="kpi-grid",
    )


def _dropdown_options(values: list[str]) -> list[dict[str, str]]:
    """Convert raw values into Dash dropdown options."""
    return [{"label": value, "value": value} for value in values if value]
