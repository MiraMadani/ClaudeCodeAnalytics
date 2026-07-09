"""DuckDB schema definitions for the analytics database."""

from __future__ import annotations

import duckdb


EMPLOYEES_TABLE = "employees"
TELEMETRY_EVENTS_TABLE = "telemetry_events"


def create_schema(connection: duckdb.DuckDBPyConnection) -> None:
    """Create all database tables if they do not already exist."""
    create_employees_table(connection)
    create_telemetry_events_table(connection)


def create_employees_table(connection: duckdb.DuckDBPyConnection) -> None:
    """Create the employee dimension table."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS employees (
            email VARCHAR PRIMARY KEY,
            full_name VARCHAR NOT NULL,
            practice VARCHAR NOT NULL,
            level VARCHAR NOT NULL,
            location VARCHAR NOT NULL
        )
        """
    )


def create_telemetry_events_table(connection: duckdb.DuckDBPyConnection) -> None:
    """Create the normalized telemetry event table.

    The table keeps one row per flattened telemetry event. Event-specific
    fields are nullable because different event names carry different metrics.
    Raw nested JSON sections are retained for auditability and future schema
    evolution.
    """
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry_events (
            event_id VARCHAR PRIMARY KEY,
            source_file VARCHAR,
            line_number INTEGER,
            event_index INTEGER,
            message_type VARCHAR,
            owner VARCHAR,
            log_group VARCHAR,
            log_stream VARCHAR,
            subscription_filters JSON,
            year INTEGER,
            month INTEGER,
            day INTEGER,
            outer_timestamp_ms BIGINT,
            raw_message VARCHAR,
            body VARCHAR,
            scope_name VARCHAR,
            scope_version VARCHAR,
            event_timestamp TIMESTAMPTZ NOT NULL,
            event_date DATE,
            event_name VARCHAR NOT NULL,
            organization_id VARCHAR,
            session_id VARCHAR NOT NULL,
            terminal_type VARCHAR,
            user_account_uuid VARCHAR,
            user_email VARCHAR NOT NULL,
            user_id VARCHAR,
            prompt VARCHAR,
            prompt_length BIGINT,
            prompt_redacted BOOLEAN,
            model VARCHAR,
            cost_usd DOUBLE,
            duration_ms BIGINT,
            input_tokens BIGINT,
            output_tokens BIGINT,
            cache_creation_tokens BIGINT,
            cache_read_tokens BIGINT,
            decision VARCHAR,
            source VARCHAR,
            tool_name VARCHAR,
            decision_source VARCHAR,
            decision_type VARCHAR,
            success BOOLEAN,
            tool_result_size_bytes BIGINT,
            status_code VARCHAR,
            error VARCHAR,
            attempt INTEGER,
            host_arch VARCHAR,
            host_name VARCHAR,
            os_type VARCHAR,
            os_version VARCHAR,
            service_name VARCHAR,
            service_version VARCHAR,
            resource_user_email VARCHAR,
            resource_user_practice VARCHAR,
            resource_user_profile VARCHAR,
            resource_user_serial VARCHAR,
            attributes_json JSON,
            resource_json JSON,
            raw_message_json JSON,
            is_malformed BOOLEAN,
            parse_error VARCHAR
        )
        """
    )
