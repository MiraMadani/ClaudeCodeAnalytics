"""Dash application entry point."""

from __future__ import annotations

from typing import Any

import pandas as pd
from dash import Dash

from analytics.metrics import filter_options
from dashboard.callbacks import register_callbacks
from dashboard.layout import create_layout
from database.connection import DEFAULT_DATABASE_PATH, connect


def create_app(database_path: str = str(DEFAULT_DATABASE_PATH)) -> Dash:
    """Create and configure the Dash app."""
    connection = connect(database_path)
    app = Dash(__name__, title="Claude Code Analytics")
    app.layout = create_layout(_load_filter_options(connection))
    app.index_string = _index_template()
    register_callbacks(app, connection)
    return app


def _load_filter_options(connection: Any) -> dict[str, Any]:
    """Load filter options through the analytics layer."""
    options = filter_options(connection)
    if options.empty:
        return {"min_date": None, "max_date": None, "practices": [], "models": []}

    row = options.iloc[0]
    return {
        "min_date": _date_string(row["min_date"]),
        "max_date": _date_string(row["max_date"]),
        "practices": _list_value(row["practices"]),
        "models": _list_value(row["models"]),
    }


def _date_string(value: object) -> str | None:
    """Convert a database date value to Dash's date string format."""
    if value is None or pd.isna(value):
        return None
    return pd.to_datetime(value).strftime("%Y-%m-%d")


def _list_value(value: object) -> list[str]:
    """Normalize DuckDB list results into plain Python strings."""
    if value is None or (hasattr(value, "__len__") and len(value) == 0):
        return []
    return [str(item) for item in list(value) if item is not None]


def _index_template() -> str:
    """Return a small HTML shell with dashboard styling."""
    return """
    <!DOCTYPE html>
    <html>
        <head>
            {%metas%}
            <title>{%title%}</title>
            {%favicon%}
            {%css%}
            <style>
                body {
                    margin: 0;
                    font-family: Arial, sans-serif;
                    background: #f6f7f9;
                    color: #1f2933;
                }
                .app-shell {
                    max-width: 1440px;
                    margin: 0 auto;
                    padding: 24px;
                }
                .app-header {
                    margin-bottom: 20px;
                }
                .app-header h1 {
                    margin: 0 0 4px;
                    font-size: 28px;
                }
                .app-header p {
                    margin: 0;
                    color: #637083;
                }
                .filters,
                .kpi-grid,
                .chart-grid {
                    display: grid;
                    gap: 16px;
                }
                .filters {
                    grid-template-columns: repeat(3, minmax(220px, 1fr));
                    align-items: end;
                    margin-bottom: 16px;
                }
                .filter-control label {
                    display: block;
                    margin-bottom: 6px;
                    font-size: 13px;
                    font-weight: 700;
                }
                .kpi-grid {
                    grid-template-columns: repeat(5, minmax(150px, 1fr));
                    margin-bottom: 16px;
                }
                .kpi-card {
                    background: white;
                    border: 1px solid #d9dee7;
                    border-radius: 8px;
                    padding: 16px;
                }
                .kpi-label {
                    display: block;
                    color: #637083;
                    font-size: 13px;
                    margin-bottom: 8px;
                }
                .kpi-card strong {
                    font-size: 24px;
                }
                .chart-grid {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }
                .chart-grid > div {
                    background: white;
                    border: 1px solid #d9dee7;
                    border-radius: 8px;
                }
                @media (max-width: 900px) {
                    .filters,
                    .kpi-grid,
                    .chart-grid {
                        grid-template-columns: 1fr;
                    }
                }
            </style>
        </head>
        <body>
            {%app_entry%}
            <footer>
                {%config%}
                {%scripts%}
                {%renderer%}
            </footer>
        </body>
    </html>
    """


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8050, debug=False)
