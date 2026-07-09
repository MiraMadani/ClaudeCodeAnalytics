"""Clean and normalize ingestion DataFrames."""

from __future__ import annotations

import re
from typing import Iterable

import pandas as pd


TELEMETRY_REQUIRED_COLUMNS = ("event_id", "event_timestamp", "event_name")
EMPLOYEE_REQUIRED_COLUMNS = ("email", "full_name", "practice", "level", "location")

NUMERIC_COLUMNS = (
    "outer_timestamp_ms",
    "year",
    "month",
    "day",
    "prompt_length",
    "cost_usd",
    "duration_ms",
    "input_tokens",
    "output_tokens",
    "cache_creation_tokens",
    "cache_read_tokens",
    "tool_result_size_bytes",
    "attempt",
)

STRING_COLUMNS = (
    "event_id",
    "message_type",
    "owner",
    "log_group",
    "log_stream",
    "body",
    "scope_name",
    "scope_version",
    "event_name",
    "organization_id",
    "session_id",
    "terminal_type",
    "user_account_uuid",
    "user_email",
    "user_id",
    "prompt",
    "model",
    "decision",
    "source",
    "tool_name",
    "decision_source",
    "decision_type",
    "status_code",
    "error",
    "host_arch",
    "host_name",
    "os_type",
    "os_version",
    "service_name",
    "service_version",
    "resource_user_email",
    "resource_user_practice",
    "resource_user_profile",
    "resource_user_serial",
)


def clean_telemetry_events(df: pd.DataFrame) -> pd.DataFrame:
    """Clean flattened telemetry events.

    Malformed rows are removed here instead of in the loader so parse failures
    can still be inspected before cleaning.
    """
    cleaned = standardize_column_names(df)
    cleaned = _drop_malformed_records(cleaned)
    cleaned = _drop_missing_required(cleaned, TELEMETRY_REQUIRED_COLUMNS)
    cleaned = _normalize_timestamps(cleaned, ("event_timestamp",))
    cleaned = _normalize_event_date(cleaned)
    cleaned = _convert_numeric_columns(cleaned, NUMERIC_COLUMNS)
    cleaned = _convert_boolean_columns(cleaned, ("success",))
    cleaned = _clean_string_columns(cleaned, STRING_COLUMNS)
    cleaned = _normalize_prompt_redaction(cleaned)
    return cleaned.reset_index(drop=True)


def clean_employees(df: pd.DataFrame) -> pd.DataFrame:
    """Clean employee dimension data."""
    cleaned = standardize_column_names(df)
    cleaned = _drop_missing_required(cleaned, EMPLOYEE_REQUIRED_COLUMNS)
    cleaned = _clean_string_columns(cleaned, EMPLOYEE_REQUIRED_COLUMNS)
    cleaned["email"] = cleaned["email"].str.lower()
    cleaned = cleaned.drop_duplicates(subset=["email"], keep="first")
    return cleaned.reset_index(drop=True)


def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with snake_case column names."""
    renamed = {
        column: _to_snake_case(str(column))
        for column in df.columns
    }
    return df.rename(columns=renamed).copy()


def _to_snake_case(value: str) -> str:
    """Convert a column name to snake_case."""
    value = re.sub(r"[^0-9a-zA-Z]+", "_", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return value.strip("_").lower()


def _drop_malformed_records(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows marked as malformed by the loader."""
    if "is_malformed" not in df.columns:
        return df.copy()
    return df[df["is_malformed"] != True].copy()  # noqa: E712


def _drop_missing_required(
    df: pd.DataFrame,
    required_columns: Iterable[str],
) -> pd.DataFrame:
    """Drop rows missing required values."""
    existing_required = [column for column in required_columns if column in df.columns]
    if not existing_required:
        return df.copy()
    return df.dropna(subset=existing_required).copy()


def _normalize_timestamps(
    df: pd.DataFrame,
    columns: Iterable[str],
) -> pd.DataFrame:
    """Convert timestamp columns to timezone-aware pandas datetimes."""
    normalized = df.copy()
    for column in columns:
        if column in normalized.columns:
            normalized[column] = pd.to_datetime(
                normalized[column],
                errors="coerce",
                utc=True,
            )
    return normalized.dropna(subset=[column for column in columns if column in normalized])


def _normalize_event_date(df: pd.DataFrame) -> pd.DataFrame:
    """Add an event_date column from event_timestamp."""
    normalized = df.copy()
    if "event_timestamp" in normalized.columns:
        normalized["event_date"] = normalized["event_timestamp"].dt.date
    return normalized


def _convert_numeric_columns(
    df: pd.DataFrame,
    columns: Iterable[str],
) -> pd.DataFrame:
    """Convert numeric columns while preserving missing values."""
    converted = df.copy()
    for column in columns:
        if column in converted.columns:
            converted[column] = pd.to_numeric(converted[column], errors="coerce")
    return converted


def _convert_boolean_columns(
    df: pd.DataFrame,
    columns: Iterable[str],
) -> pd.DataFrame:
    """Convert string boolean columns to nullable booleans."""
    converted = df.copy()
    for column in columns:
        if column in converted.columns:
            converted[column] = converted[column].map(_to_nullable_bool).astype("boolean")
    return converted


def _to_nullable_bool(value: object) -> bool | pd.NA:
    """Convert common boolean representations to bool or NA."""
    if pd.isna(value):
        return pd.NA
    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    return pd.NA


def _clean_string_columns(
    df: pd.DataFrame,
    columns: Iterable[str],
) -> pd.DataFrame:
    """Trim strings and replace empty strings with missing values."""
    cleaned = df.copy()
    for column in columns:
        if column in cleaned.columns:
            cleaned[column] = cleaned[column].astype("string").str.strip()
            cleaned[column] = cleaned[column].replace("", pd.NA)
    return cleaned


def _normalize_prompt_redaction(df: pd.DataFrame) -> pd.DataFrame:
    """Add a boolean flag for redacted prompts."""
    normalized = df.copy()
    if "prompt" in normalized.columns:
        normalized["prompt_redacted"] = normalized["prompt"].eq("<REDACTED>").astype("boolean")
    return normalized
