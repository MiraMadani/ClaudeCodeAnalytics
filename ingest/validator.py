"""Validation helpers for ingestion DataFrames."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd
from pandas.api.types import (
    is_bool_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_string_dtype,
)


class ValidationError(ValueError):
    """Raised when an ingestion DataFrame fails validation."""


TELEMETRY_REQUIRED_COLUMNS = (
    "event_id",
    "event_timestamp",
    "event_name",
    "user_email",
    "session_id",
)

EMPLOYEE_REQUIRED_COLUMNS = (
    "email",
    "full_name",
    "practice",
    "level",
    "location",
)

TELEMETRY_TYPE_RULES = {
    "event_id": "string",
    "event_timestamp": "datetime",
    "event_name": "string",
    "user_email": "string",
    "session_id": "string",
    "cost_usd": "numeric",
    "duration_ms": "numeric",
    "input_tokens": "numeric",
    "output_tokens": "numeric",
    "cache_creation_tokens": "numeric",
    "cache_read_tokens": "numeric",
    "success": "boolean",
}

EMPLOYEE_TYPE_RULES = {
    "email": "string",
    "full_name": "string",
    "practice": "string",
    "level": "string",
    "location": "string",
}


def validate_telemetry_events(df: pd.DataFrame) -> None:
    """Validate cleaned telemetry events.

    Raises:
        ValidationError: If required columns, values, data types, or timestamps
            are invalid.
    """
    _validate_not_empty(df, "telemetry events")
    validate_required_columns(df, TELEMETRY_REQUIRED_COLUMNS, "telemetry events")
    validate_required_values(df, TELEMETRY_REQUIRED_COLUMNS, "telemetry events")
    validate_data_types(df, TELEMETRY_TYPE_RULES, "telemetry events")
    validate_timestamps(df, "event_timestamp", "telemetry events")


def validate_employees(df: pd.DataFrame) -> None:
    """Validate cleaned employee data.

    Raises:
        ValidationError: If required columns, values, data types, or keys are
            invalid.
    """
    _validate_not_empty(df, "employees")
    validate_required_columns(df, EMPLOYEE_REQUIRED_COLUMNS, "employees")
    validate_required_values(df, EMPLOYEE_REQUIRED_COLUMNS, "employees")
    validate_data_types(df, EMPLOYEE_TYPE_RULES, "employees")
    _validate_unique_key(df, "email", "employees")


def validate_required_columns(
    df: pd.DataFrame,
    required_columns: Sequence[str],
    dataset_name: str,
) -> None:
    """Validate that all required columns are present."""
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValidationError(
            f"{dataset_name} is missing required columns: {', '.join(missing)}"
        )


def validate_required_values(
    df: pd.DataFrame,
    required_columns: Sequence[str],
    dataset_name: str,
) -> None:
    """Validate that required columns do not contain missing values."""
    missing_counts = {
        column: int(df[column].isna().sum())
        for column in required_columns
        if column in df.columns and df[column].isna().any()
    }
    if missing_counts:
        formatted = _format_counts(missing_counts)
        raise ValidationError(f"{dataset_name} has missing required values: {formatted}")


def validate_data_types(
    df: pd.DataFrame,
    type_rules: Mapping[str, str],
    dataset_name: str,
) -> None:
    """Validate column data types for columns present in a DataFrame."""
    failures = []
    for column, expected_type in type_rules.items():
        if column not in df.columns:
            continue
        if not _matches_expected_type(df[column], expected_type):
            failures.append(f"{column} expected {expected_type}, got {df[column].dtype}")

    if failures:
        raise ValidationError(
            f"{dataset_name} has invalid column types: {'; '.join(failures)}"
        )


def validate_timestamps(
    df: pd.DataFrame,
    timestamp_column: str,
    dataset_name: str,
) -> None:
    """Validate that a timestamp column is typed and contains valid values."""
    if timestamp_column not in df.columns:
        raise ValidationError(
            f"{dataset_name} is missing timestamp column: {timestamp_column}"
        )
    if not is_datetime64_any_dtype(df[timestamp_column]):
        raise ValidationError(
            f"{dataset_name}.{timestamp_column} must be datetime64, "
            f"got {df[timestamp_column].dtype}"
        )
    if df[timestamp_column].isna().any():
        missing_count = int(df[timestamp_column].isna().sum())
        raise ValidationError(
            f"{dataset_name}.{timestamp_column} contains {missing_count} invalid timestamps"
        )


def _validate_not_empty(df: pd.DataFrame, dataset_name: str) -> None:
    """Validate that a DataFrame contains at least one row."""
    if df.empty:
        raise ValidationError(f"{dataset_name} is empty")


def _validate_unique_key(
    df: pd.DataFrame,
    key_column: str,
    dataset_name: str,
) -> None:
    """Validate that a key column contains unique values."""
    duplicate_count = int(df[key_column].duplicated().sum())
    if duplicate_count:
        raise ValidationError(
            f"{dataset_name}.{key_column} contains {duplicate_count} duplicate values"
        )


def _matches_expected_type(series: pd.Series, expected_type: str) -> bool:
    """Return whether a Series matches a named expected type."""
    if expected_type == "string":
        return is_string_dtype(series) or series.dtype == object
    if expected_type == "numeric":
        return is_numeric_dtype(series)
    if expected_type == "datetime":
        return is_datetime64_any_dtype(series)
    if expected_type == "boolean":
        return is_bool_dtype(series)
    raise ValidationError(f"Unsupported validation type: {expected_type}")


def _format_counts(counts: Mapping[str, int]) -> str:
    """Format missing-value counts for exception messages."""
    return ", ".join(f"{column}={count}" for column, count in counts.items())
