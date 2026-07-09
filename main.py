"""Run the Claude Code Analytics ETL pipeline."""

from __future__ import annotations

from ingest.cleaner import clean_employees, clean_telemetry_events
from ingest.loader import load_datasets
from ingest.validator import (
    validate_employees,
    validate_telemetry_events,
)

from database.connection import managed_connection
from database.repository import (
    save_employees,
    save_telemetry_events,
)


def main() -> None:
    """Execute the complete ETL pipeline."""

    print("Loading datasets...")
    telemetry_df, employees_df = load_datasets()

    print("Cleaning data...")
    telemetry_df = clean_telemetry_events(telemetry_df)
    employees_df = clean_employees(employees_df)

    print("Validating data...")
    validate_telemetry_events(telemetry_df)
    validate_employees(employees_df)

    print("Saving to DuckDB...")
    with managed_connection() as connection:
        employee_count = save_employees(connection, employees_df)
        telemetry_count = save_telemetry_events(connection, telemetry_df)

    print()
    print("ETL completed successfully.")
    print(f"Employees loaded : {employee_count}")
    print(f"Telemetry loaded : {telemetry_count}")


if __name__ == "__main__":
    main()