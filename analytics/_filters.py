"""Shared SQL filter helpers for analytics queries."""

from __future__ import annotations

from typing import Any


def employee_join(alias: str = "t") -> str:
    """Return the employee join used for practice filtering."""
    return f"LEFT JOIN employees AS e ON {alias}.user_email = e.email"


def event_filters(
    *,
    alias: str = "t",
    start_date: str | None = None,
    end_date: str | None = None,
    practice: str | None = None,
    model: str | None = None,
    event_name: str | None = None,
    model_by_session: bool = False,
) -> tuple[list[str], list[Any]]:
    """Build parameterized WHERE clauses for event analytics."""
    clauses: list[str] = []
    params: list[Any] = []

    if event_name is not None:
        clauses.append(f"{alias}.event_name = ?")
        params.append(event_name)
    if start_date is not None:
        clauses.append(f"{alias}.event_timestamp >= CAST(? AS TIMESTAMPTZ)")
        params.append(start_date)
    if end_date is not None:
        clauses.append(f"{alias}.event_timestamp < CAST(? AS TIMESTAMPTZ)")
        params.append(end_date)
    if practice is not None:
        clauses.append("COALESCE(e.practice, t.resource_user_practice) = ?")
        params.append(practice)
    if model is not None and model_by_session:
        clauses.append(
            f"""
            EXISTS (
                SELECT 1
                FROM telemetry_events AS model_events
                WHERE model_events.session_id = {alias}.session_id
                    AND model_events.event_name = 'api_request'
                    AND model_events.model = ?
            )
            """
        )
        params.append(model)
    elif model is not None:
        clauses.append(f"{alias}.model = ?")
        params.append(model)

    return clauses, params


def where_sql(clauses: list[str]) -> str:
    """Render WHERE SQL for a list of clauses."""
    if not clauses:
        return ""
    return "WHERE " + " AND ".join(clauses)
