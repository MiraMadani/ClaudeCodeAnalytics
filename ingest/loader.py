"""Load raw telemetry and employee files into pandas DataFrames."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


PathLike = str | Path


def load_datasets(
    telemetry_path: PathLike = "data/telemetry_logs.jsonl",
    employees_path: PathLike = "data/employees.csv",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load telemetry and employee datasets.

    Returns:
        A tuple of ``(telemetry_events, employees)`` DataFrames.
    """
    return load_telemetry_logs(telemetry_path), load_employees(employees_path)


def load_employees(path: PathLike = "data/employees.csv") -> pd.DataFrame:
    """Load employee metadata from CSV."""
    return pd.read_csv(_resolve_path(path))


def load_telemetry_logs(path: PathLike = "data/telemetry_logs.jsonl") -> pd.DataFrame:
    """Load and flatten telemetry JSONL batches.

    Each JSONL line is a CloudWatch-style batch. Each batch contains
    ``logEvents`` entries, and each event contains a nested JSON string in its
    ``message`` field. This function returns one DataFrame row per flattened
    log event.
    """
    source_path = _resolve_path(path)
    records: list[dict[str, Any]] = []

    with source_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            records.extend(_parse_batch_line(line, source_path, line_number))

    return pd.DataFrame.from_records(records)


def _resolve_path(path: PathLike) -> Path:
    """Return a Path and fail clearly when it does not exist."""
    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Input file does not exist: {resolved}")
    if not resolved.is_file():
        raise ValueError(f"Input path is not a file: {resolved}")
    return resolved


def _parse_batch_line(
    line: str,
    source_path: Path,
    line_number: int,
) -> list[dict[str, Any]]:
    """Parse one top-level JSONL line into event records."""
    try:
        batch = json.loads(line)
    except json.JSONDecodeError as exc:
        return [_malformed_record(source_path, line_number, str(exc), line)]

    return _flatten_batch(batch, source_path, line_number)


def _flatten_batch(
    batch: dict[str, Any],
    source_path: Path,
    line_number: int,
) -> list[dict[str, Any]]:
    """Flatten all log events from a parsed top-level batch."""
    batch_context = _batch_context(batch, source_path, line_number)
    log_events = batch.get("logEvents")

    if not isinstance(log_events, list):
        return [
            {
                **batch_context,
                "is_malformed": True,
                "parse_error": "Top-level logEvents field is missing or not a list.",
                "raw_message": json.dumps(batch),
            }
        ]

    return [
        _flatten_log_event(event, batch_context, event_index)
        for event_index, event in enumerate(log_events)
    ]


def _batch_context(
    batch: dict[str, Any],
    source_path: Path,
    line_number: int,
) -> dict[str, Any]:
    """Extract fields shared by every event in a top-level batch."""
    return {
        "source_file": str(source_path),
        "line_number": line_number,
        "message_type": batch.get("messageType"),
        "owner": batch.get("owner"),
        "log_group": batch.get("logGroup"),
        "log_stream": batch.get("logStream"),
        "subscription_filters": batch.get("subscriptionFilters"),
        "year": batch.get("year"),
        "month": batch.get("month"),
        "day": batch.get("day"),
    }


def _flatten_log_event(
    event: Any,
    batch_context: dict[str, Any],
    event_index: int,
) -> dict[str, Any]:
    """Flatten one logEvents item and its nested message JSON."""
    if not isinstance(event, dict):
        return {
            **batch_context,
            "event_index": event_index,
            "is_malformed": True,
            "parse_error": "logEvents item is not an object.",
            "raw_message": json.dumps(event),
        }

    base_record = _event_context(event, batch_context, event_index)
    message = event.get("message")

    if not isinstance(message, str):
        return {
            **base_record,
            "is_malformed": True,
            "parse_error": "logEvents.message is missing or not a string.",
        }

    try:
        nested_message = json.loads(message)
    except json.JSONDecodeError as exc:
        return {
            **base_record,
            "is_malformed": True,
            "parse_error": f"Nested message JSON parse failed: {exc}",
        }

    return {
        **base_record,
        **_nested_message_fields(nested_message),
        "is_malformed": False,
        "parse_error": None,
    }


def _event_context(
    event: dict[str, Any],
    batch_context: dict[str, Any],
    event_index: int,
) -> dict[str, Any]:
    """Extract fields from the outer log event wrapper."""
    return {
        **batch_context,
        "event_index": event_index,
        "event_id": event.get("id"),
        "outer_timestamp_ms": event.get("timestamp"),
        "raw_message": event.get("message"),
    }


def _nested_message_fields(message: dict[str, Any]) -> dict[str, Any]:
    """Extract normalized columns from a parsed nested telemetry message."""
    attributes = _safe_dict(message.get("attributes"))
    resource = _safe_dict(message.get("resource"))
    scope = _safe_dict(message.get("scope"))

    return {
        "body": message.get("body"),
        "scope_name": scope.get("name"),
        "scope_version": scope.get("version"),
        "event_timestamp": attributes.get("event.timestamp"),
        "event_name": attributes.get("event.name"),
        "organization_id": attributes.get("organization.id"),
        "session_id": attributes.get("session.id"),
        "terminal_type": attributes.get("terminal.type"),
        "user_account_uuid": attributes.get("user.account_uuid"),
        "user_email": attributes.get("user.email"),
        "user_id": attributes.get("user.id"),
        "prompt": attributes.get("prompt"),
        "prompt_length": attributes.get("prompt_length"),
        "model": attributes.get("model"),
        "cost_usd": attributes.get("cost_usd"),
        "duration_ms": attributes.get("duration_ms"),
        "input_tokens": attributes.get("input_tokens"),
        "output_tokens": attributes.get("output_tokens"),
        "cache_creation_tokens": attributes.get("cache_creation_tokens"),
        "cache_read_tokens": attributes.get("cache_read_tokens"),
        "decision": attributes.get("decision"),
        "source": attributes.get("source"),
        "tool_name": attributes.get("tool_name"),
        "decision_source": attributes.get("decision_source"),
        "decision_type": attributes.get("decision_type"),
        "success": attributes.get("success"),
        "tool_result_size_bytes": attributes.get("tool_result_size_bytes"),
        "status_code": attributes.get("status_code"),
        "error": attributes.get("error"),
        "attempt": attributes.get("attempt"),
        "host_arch": resource.get("host.arch"),
        "host_name": resource.get("host.name"),
        "os_type": resource.get("os.type"),
        "os_version": resource.get("os.version"),
        "service_name": resource.get("service.name"),
        "service_version": resource.get("service.version"),
        "resource_user_email": resource.get("user.email"),
        "resource_user_practice": resource.get("user.practice"),
        "resource_user_profile": resource.get("user.profile"),
        "resource_user_serial": resource.get("user.serial"),
        "attributes_json": attributes,
        "resource_json": resource,
        "raw_message_json": message,
    }


def _safe_dict(value: Any) -> dict[str, Any]:
    """Return a dictionary for nested message sections."""
    return value if isinstance(value, dict) else {}


def _malformed_record(
    source_path: Path,
    line_number: int,
    error: str,
    raw_message: str,
) -> dict[str, Any]:
    """Build a row for a malformed top-level JSONL record."""
    return {
        "source_file": str(source_path),
        "line_number": line_number,
        "event_index": None,
        "event_id": None,
        "outer_timestamp_ms": None,
        "is_malformed": True,
        "parse_error": f"Top-level JSON parse failed: {error}",
        "raw_message": raw_message,
    }
