# Architecture

## Purpose

This project analyzes Claude Code telemetry and employee metadata to answer questions about adoption, cost, reliability, tool usage, and team-level usage patterns.

The architecture is intentionally local and analytical: files are ingested, normalized into DuckDB, queried through reusable analytics modules, and presented in a dashboard.

## System Architecture

```text
                          +-------------------------+
                          |        data/            |
                          |-------------------------|
                          | telemetry_logs.jsonl    |
                          | employees.csv           |
                          +------------+------------+
                                       |
                                       v
                          +-------------------------+
                          |        ingest/          |
                          |-------------------------|
                          | loader                  |
                          | validator               |
                          | cleaner / normalizer    |
                          +------------+------------+
                                       |
                                       v
                          +-------------------------+
                          |       database/         |
                          |-------------------------|
                          | DuckDB file             |
                          | normalized tables       |
                          | aggregate views         |
                          +------------+------------+
                                       |
                                       v
                +----------------------+----------------------+
                |                                             |
                v                                             v
   +-------------------------+                    +-------------------------+
   |       analytics/        |                    |        tests/           |
   |-------------------------|                    |-------------------------|
   | KPI queries             |                    | parser tests            |
   | reusable aggregations   |                    | schema tests            |
   | metric definitions      |                    | metric tests            |
   +------------+------------+                    +-------------------------+
                |
                v
   +-------------------------+
   |       dashboard/        |
   |-------------------------|
   | Dash app                |
   | Plotly charts          |
   | filters and pages      |
   +-------------------------+
```

## Folder Responsibilities

| Folder | Responsibility |
| --- | --- |
| `data/` | Source datasets. Keep raw input files unchanged so ingestion is repeatable and auditable. |
| `ingest/` | File loading, JSONL batch parsing, nested message parsing, validation, cleaning, and type normalization. |
| `database/` | DuckDB database file, schema setup assets, and persisted analytical tables or views. |
| `analytics/` | Reusable metric definitions and query functions for cost, adoption, sessions, tools, errors, and data quality. |
| `dashboard/` | Dash and Plotly presentation layer. It should consume analytics outputs rather than reimplement metrics. |
| `tests/` | Unit and integration tests for parsing, validation, schema loading, joins, and KPI calculations. |
| `docs/` | Project design notes, data analysis, architecture, and operational guidance. |
| `agent/` | Reserved for future agent-facing workflows or automation if needed. It should not own core analytics logic. |

## Data Pipeline

### 1. Load Raw Sources

- Read `data/telemetry_logs.jsonl` as streaming JSON Lines.
- Read `data/employees.csv` as a small dimension table.
- Keep source files immutable during processing.

### 2. Parse Telemetry Batches

Each JSONL line is a top-level log batch with fields such as `messageType`, `owner`, `logGroup`, `logStream`, `subscriptionFilters`, `logEvents`, `year`, `month`, and `day`.

The pipeline should flatten each `logEvents` entry into one event row. For every `logEvents` item:

- Use `logEvents.id` as the stable event identifier.
- Preserve `logEvents.timestamp` as the outer timestamp.
- Parse `logEvents.message`, which is itself a JSON string.
- Extract `body`, `attributes`, `scope`, and `resource` from the parsed message.

### 3. Normalize Fields

The nested `attributes` values are mostly strings, even when they represent numbers or booleans. Normalization should:

- Convert timestamps to `TIMESTAMP`.
- Convert cost to `DOUBLE`.
- Convert token, duration, prompt length, result size, and attempt fields to integer types.
- Convert success flags to `BOOLEAN`.
- Normalize absent or invalid status codes into explicit nullable values or an `undefined` category.
- Use `attributes.user.email` as the employee join key because `resource.user.email` is empty in observed samples.

### 4. Validate and Quarantine Bad Rows

Validation should happen before loading facts into analytics tables:

- Required event identifiers and timestamps must be present.
- Nested JSON parse failures should be captured.
- Unknown event names should be retained in `telemetry_events`, even if they do not map to a specialized fact table yet.
- Rows that cannot be normalized should be written to a reject table with the raw payload and reason.

### 5. Load DuckDB

Load data into DuckDB in layers:

- Raw or lightly parsed event table for auditability.
- Normalized base event table.
- Specialized fact tables by event type.
- Dimension tables for employees, users, models, tools, terminals, and dates when useful.
- Views or aggregate tables for dashboard-ready metrics.

### 6. Compute Analytics

Analytics modules should query DuckDB and return data frames or simple records for the dashboard:

- Adoption and engagement metrics
- Cost and token metrics
- Model usage metrics
- Tool usage and success metrics
- Reliability and error metrics
- Organization, practice, level, and location breakdowns
- Data quality metrics

### 7. Serve Dashboard

The dashboard should read from DuckDB through the analytics layer. It should not parse raw files directly.

Common filters:

- Date range
- Practice
- Level
- Location
- User
- Model
- Tool
- Terminal type

## DuckDB Schema

DuckDB is the recommended local analytical store for this project. It handles nested-source ingestion well, supports SQL analytics directly, works with pandas and Dash, and is suitable for the current dataset size.

### `employees`

One row per employee.

| Column | Type | Notes |
| --- | --- | --- |
| `email` | `VARCHAR` | Primary employee key and telemetry join key. |
| `full_name` | `VARCHAR` | Display name. |
| `practice` | `VARCHAR` | Team or discipline. |
| `level` | `VARCHAR` | Career level such as `L4`. |
| `location` | `VARCHAR` | Employee location. |

### `raw_log_batches`

One row per top-level JSONL line.

| Column | Type | Notes |
| --- | --- | --- |
| `batch_id` | `VARCHAR` | Deterministic generated ID, for example file name plus line number or hash. |
| `source_file` | `VARCHAR` | Source file path. |
| `line_number` | `INTEGER` | JSONL line number. |
| `message_type` | `VARCHAR` | Top-level `messageType`. |
| `owner` | `VARCHAR` | Top-level owner. |
| `log_group` | `VARCHAR` | Top-level log group. |
| `log_stream` | `VARCHAR` | Top-level log stream. |
| `year` | `INTEGER` | Top-level partition year. |
| `month` | `INTEGER` | Top-level partition month. |
| `day` | `INTEGER` | Top-level partition day. |
| `event_count` | `INTEGER` | Number of entries in `logEvents`. |
| `raw_json` | `JSON` | Original top-level row. |

### `telemetry_events`

One row per flattened `logEvents` entry.

| Column | Type | Notes |
| --- | --- | --- |
| `event_id` | `VARCHAR` | Source `logEvents.id`; primary event key. |
| `batch_id` | `VARCHAR` | Link to `raw_log_batches`. |
| `outer_timestamp_ms` | `BIGINT` | Source `logEvents.timestamp`. |
| `event_timestamp` | `TIMESTAMP` | Parsed `attributes.event.timestamp`; canonical analytics timestamp. |
| `event_date` | `DATE` | Derived from `event_timestamp`. |
| `body` | `VARCHAR` | Inner message body, such as `claude_code.api_request`. |
| `event_name` | `VARCHAR` | `attributes.event.name`. |
| `organization_id` | `VARCHAR` | Organization identifier. |
| `session_id` | `VARCHAR` | Session identifier. |
| `user_email` | `VARCHAR` | Join key to `employees.email`. |
| `user_id` | `VARCHAR` | Opaque user identifier. |
| `user_account_uuid` | `VARCHAR` | Account UUID. |
| `terminal_type` | `VARCHAR` | IDE or terminal. |
| `host_arch` | `VARCHAR` | Resource host architecture. |
| `host_name` | `VARCHAR` | Resource host name. |
| `os_type` | `VARCHAR` | Resource OS type. |
| `os_version` | `VARCHAR` | Resource OS version. |
| `service_name` | `VARCHAR` | Resource service name. |
| `service_version` | `VARCHAR` | Resource service version. |
| `resource_user_practice` | `VARCHAR` | Practice from resource payload. |
| `resource_user_profile` | `VARCHAR` | User profile from resource payload. |
| `resource_user_serial` | `VARCHAR` | Device or serial identifier from resource payload. |
| `attributes_json` | `JSON` | Full parsed attributes payload. |
| `resource_json` | `JSON` | Full parsed resource payload. |
| `raw_message_json` | `JSON` | Full parsed nested message. |

### `api_requests`

One row per `api_request` event.

| Column | Type | Notes |
| --- | --- | --- |
| `event_id` | `VARCHAR` | References `telemetry_events.event_id`. |
| `event_timestamp` | `TIMESTAMP` | Canonical event timestamp. |
| `event_date` | `DATE` | Derived date. |
| `user_email` | `VARCHAR` | Join key to employees. |
| `session_id` | `VARCHAR` | Session identifier. |
| `organization_id` | `VARCHAR` | Organization identifier. |
| `terminal_type` | `VARCHAR` | IDE or terminal. |
| `model` | `VARCHAR` | Model name. |
| `cost_usd` | `DOUBLE` | Request cost. |
| `duration_ms` | `BIGINT` | Request duration. |
| `input_tokens` | `BIGINT` | Input tokens. |
| `output_tokens` | `BIGINT` | Output tokens. |
| `cache_creation_tokens` | `BIGINT` | Cache creation tokens. |
| `cache_read_tokens` | `BIGINT` | Cache read tokens. |

### `api_errors`

One row per `api_error` event.

| Column | Type | Notes |
| --- | --- | --- |
| `event_id` | `VARCHAR` | References `telemetry_events.event_id`. |
| `event_timestamp` | `TIMESTAMP` | Canonical event timestamp. |
| `event_date` | `DATE` | Derived date. |
| `user_email` | `VARCHAR` | Join key to employees. |
| `session_id` | `VARCHAR` | Session identifier. |
| `organization_id` | `VARCHAR` | Organization identifier. |
| `terminal_type` | `VARCHAR` | IDE or terminal. |
| `model` | `VARCHAR` | Model name when present. |
| `status_code` | `VARCHAR` | Keep as text to preserve values such as `undefined`. |
| `error` | `VARCHAR` | Error message. |
| `attempt` | `INTEGER` | Attempt number when present. |

### `user_prompts`

One row per `user_prompt` event.

| Column | Type | Notes |
| --- | --- | --- |
| `event_id` | `VARCHAR` | References `telemetry_events.event_id`. |
| `event_timestamp` | `TIMESTAMP` | Canonical event timestamp. |
| `event_date` | `DATE` | Derived date. |
| `user_email` | `VARCHAR` | Join key to employees. |
| `session_id` | `VARCHAR` | Session identifier. |
| `organization_id` | `VARCHAR` | Organization identifier. |
| `terminal_type` | `VARCHAR` | IDE or terminal. |
| `prompt_length` | `INTEGER` | Prompt length. |
| `prompt_redacted` | `BOOLEAN` | True when prompt text is redacted. |

### `tool_decisions`

One row per `tool_decision` event.

| Column | Type | Notes |
| --- | --- | --- |
| `event_id` | `VARCHAR` | References `telemetry_events.event_id`. |
| `event_timestamp` | `TIMESTAMP` | Canonical event timestamp. |
| `event_date` | `DATE` | Derived date. |
| `user_email` | `VARCHAR` | Join key to employees. |
| `session_id` | `VARCHAR` | Session identifier. |
| `organization_id` | `VARCHAR` | Organization identifier. |
| `terminal_type` | `VARCHAR` | IDE or terminal. |
| `tool_name` | `VARCHAR` | Tool name. |
| `decision` | `VARCHAR` | Decision value, such as accept or reject. |
| `source` | `VARCHAR` | Decision source. |

### `tool_results`

One row per `tool_result` event.

| Column | Type | Notes |
| --- | --- | --- |
| `event_id` | `VARCHAR` | References `telemetry_events.event_id`. |
| `event_timestamp` | `TIMESTAMP` | Canonical event timestamp. |
| `event_date` | `DATE` | Derived date. |
| `user_email` | `VARCHAR` | Join key to employees. |
| `session_id` | `VARCHAR` | Session identifier. |
| `organization_id` | `VARCHAR` | Organization identifier. |
| `terminal_type` | `VARCHAR` | IDE or terminal. |
| `tool_name` | `VARCHAR` | Tool name. |
| `success` | `BOOLEAN` | Tool success flag. |
| `duration_ms` | `BIGINT` | Tool duration. |
| `tool_result_size_bytes` | `BIGINT` | Result payload size when present. |
| `decision_type` | `VARCHAR` | Decision type from result attributes. |
| `decision_source` | `VARCHAR` | Decision source from result attributes. |

### `sessions`

One row per session, derived from event tables.

| Column | Type | Notes |
| --- | --- | --- |
| `session_id` | `VARCHAR` | Session key. |
| `user_email` | `VARCHAR` | Main user for the session. |
| `organization_id` | `VARCHAR` | Organization identifier. |
| `session_start` | `TIMESTAMP` | First event timestamp. |
| `session_end` | `TIMESTAMP` | Last event timestamp. |
| `duration_ms` | `BIGINT` | Session duration. |
| `event_count` | `INTEGER` | Total events. |
| `prompt_count` | `INTEGER` | User prompt count. |
| `api_request_count` | `INTEGER` | API request count. |
| `tool_result_count` | `INTEGER` | Tool result count. |
| `api_error_count` | `INTEGER` | API error count. |
| `total_cost_usd` | `DOUBLE` | API request cost in session. |

### Recommended Views

| View | Purpose |
| --- | --- |
| `v_events_enriched` | `telemetry_events` joined to `employees`. |
| `v_api_requests_enriched` | API requests joined to employee dimensions. |
| `v_tool_results_enriched` | Tool results joined to employee dimensions. |
| `v_daily_kpis` | Daily cost, active users, prompts, sessions, requests, errors, and success rates. |
| `v_practice_kpis` | Practice-level adoption, cost, and reliability. |
| `v_model_kpis` | Model usage, cost, token, and latency metrics. |
| `v_user_kpis` | User-level adoption and spend. |
| `v_data_quality` | Join coverage, malformed row counts, duplicate IDs, and missing required fields. |

## Dashboard Pages

### 1. Overview

Audience: engineering leadership and stakeholders.

Primary content:

- Total cost
- Active users
- Sessions
- User prompts
- API requests
- API error rate
- Tool success rate
- Daily trend for cost and active users

### 2. Cost and Models

Audience: owners of AI usage and budget.

Primary content:

- Cost by day
- Cost by model
- Cost by practice
- Cost per user
- Cost per prompt
- Token usage by model
- Cache read and cache creation trends
- High-cost sessions and users

### 3. Adoption

Audience: managers and enablement teams.

Primary content:

- Active users by practice, level, and location
- Prompts per user
- Sessions per user
- Usage by terminal type
- Practice-level usage per employee
- Level-level adoption patterns

### 4. Tools and Workflow

Audience: developer productivity and platform teams.

Primary content:

- Tool usage mix
- Tool success rate by tool
- Average tool duration
- Tool result size distribution
- Tool decisions by decision and source
- Tool activity by practice and terminal

### 5. Reliability

Audience: platform and support teams.

Primary content:

- API error rate over time
- Error counts by status code
- Error messages by frequency
- Rate limit events
- Slow API requests
- Slow tool results
- Reliability by model, terminal, and practice

### 6. Users and Sessions

Audience: team leads and analysts.

Primary content:

- User table with cost, prompts, sessions, requests, and errors
- Session table with duration, event counts, cost, and error counts
- Drilldown from user to sessions
- Drilldown from session to event timeline

### 7. Data Quality

Audience: maintainers.

Primary content:

- Parsed rows and rejected rows
- Employee join coverage
- Duplicate event IDs
- Missing timestamps
- Missing required fields by event type
- Unknown event names
- Type conversion failures

## KPIs

### Adoption KPIs

- Daily active users
- Weekly active users
- Monthly active users
- Active user rate: active users divided by employee count
- Sessions per active user
- Prompts per active user
- API requests per prompt
- Tool calls per prompt

### Cost KPIs

- Total cost
- Cost by model
- Cost by practice
- Cost by user
- Cost per active user
- Cost per prompt
- Cost per session
- Cost per 1,000 output tokens
- Cache read tokens
- Cache creation tokens
- Cache efficiency ratio: cache read tokens divided by total processed tokens

### Productivity KPIs

- Tool calls per session
- Tool success rate
- Tool failure rate
- Average tool duration
- Median tool duration
- Prompt-to-tool ratio
- Prompt-to-API-request ratio
- Session depth: events per session

### Reliability KPIs

- API error rate
- API error count by status code
- Rate limit event count
- Authentication error count
- Internal server error count
- Average API duration
- P95 API duration
- Slow request rate
- Slow tool rate

### Organizational KPIs

- Cost per employee by practice
- Active user rate by practice
- Prompts per employee by practice
- Cost by level
- Adoption by level
- Cost by location
- Adoption by location

### Data Quality KPIs

- Employee join coverage
- Raw rows parsed successfully
- Nested messages parsed successfully
- Rejected row count
- Duplicate event ID count
- Missing canonical timestamp count
- Missing user email count
- Missing numeric metric count by event type

## Testing Strategy

### Unit Tests

Unit tests should cover small, deterministic functions:

- JSONL line parsing
- Nested `logEvents.message` parsing
- Field extraction from `attributes`, `resource`, and `scope`
- Type conversion for timestamps, booleans, costs, tokens, durations, and attempts
- Redacted prompt detection
- Status code normalization

### Fixture Tests

Use small fixtures that represent the observed data shapes:

- Valid telemetry batch with multiple event types
- Malformed top-level JSONL row
- Valid top-level row with malformed nested `message`
- Event with missing optional fields
- Event with missing required fields
- Employee CSV with duplicate email
- Employee CSV with telemetry user missing

### Integration Tests

Integration tests should validate the pipeline across layers:

- Load sample telemetry and employees.
- Produce expected normalized tables.
- Confirm all specialized fact rows link back to `telemetry_events`.
- Confirm employee joins work through `attributes.user.email`.
- Confirm unknown event types remain available in `telemetry_events`.
- Confirm reject rows are written with useful reasons.

### Analytics Tests

Analytics tests should use controlled fixture data with known totals:

- Total cost
- Cost by model
- Token totals
- Active users
- Prompt counts
- Session counts
- API error rate
- Tool success rate
- Practice-level cost and usage

### Dashboard Tests

Dashboard tests should focus on data contract and page resilience:

- Each page can load from an empty-but-valid DuckDB database.
- Each page can load from representative fixture data.
- Filters return expected subsets.
- Charts handle no-data states.
- Metric cards do not fail on null or zero denominators.

## Error Handling Strategy

### Parsing Errors

Malformed top-level JSONL rows should not stop the whole pipeline. They should be written to a reject table with:

- Source file
- Line number
- Raw text when available
- Error category
- Error message

Malformed nested `logEvents.message` values should also be rejected or recorded as parse failures, while other events in the same top-level batch continue processing.

### Validation Errors

Validation should classify issues by severity:

- Fatal for a run: missing source file, unreadable database path, schema initialization failure.
- Row-level reject: malformed JSON, missing event ID, missing canonical timestamp when required.
- Warning: missing optional metric fields, unknown event type, missing employee join.

### Type Conversion Errors

Type conversion should be explicit and observable:

- Invalid numeric values become null only when the metric is optional.
- Invalid numeric values on required metrics should create a reject row.
- Invalid booleans should become null with a warning unless the event type requires them.
- Raw JSON should be retained so bad conversions can be inspected later.

### Duplicate Handling

`event_id` should be treated as the natural event key. Duplicate IDs should be detected during load.

Recommended handling:

- Keep the first valid event in fact tables.
- Record duplicate IDs in a data quality table.
- Include duplicate counts in the Data Quality dashboard.

### Join Errors

Telemetry rows without a matching employee should remain in the telemetry tables, but employee dimensions should be null. This preserves usage data while making join gaps visible.

The dashboard should expose:

- Join coverage percentage
- Users missing from `employees.csv`
- Employees without telemetry

### Analytics Errors

Analytics queries should avoid fragile assumptions:

- Use null-safe arithmetic.
- Guard division by zero.
- Treat absent dimensions as `Unknown`.
- Prefer canonical timestamps from `attributes.event.timestamp`.
- Fall back to outer log timestamps only for diagnostics, not primary KPI reporting.

### Dashboard Errors

The dashboard should degrade gracefully:

- Empty data should show empty states, not exceptions.
- Invalid filters should return no rows, not crash the app.
- Missing optional columns should be caught during startup validation.
- Expensive queries should be pre-aggregated into views or cached if needed.

## Architectural Decision Rationale

### Why DuckDB

DuckDB is a good fit because the project is analytical, local, and file-backed. It can handle tens of thousands of events easily, supports SQL aggregations, works well with pandas, and avoids the operational cost of a server database. It also leaves room to scale from the current 49,379 flattened events to much larger local telemetry exports.

### Why Keep Raw and Normalized Tables

The telemetry format has two layers of JSON parsing and many string-encoded metrics. Keeping raw payloads makes the pipeline auditable and debuggable. Normalized tables make analytics simple, typed, and repeatable.

### Why Split Fact Tables by Event Type

The event types have different fields. `api_request` events carry model, cost, tokens, and latency. `tool_result` events carry tool success and result size. `user_prompt` events carry prompt length. Splitting facts by event type avoids sparse wide tables while keeping `telemetry_events` as the common event spine.

### Why Use `attributes.user.email` for Joins

The observed `resource.user.email` value is empty, while `attributes.user.email` joins completely to `employees.csv`. Using `attributes.user.email` gives complete employee coverage for the current dataset and supports practice, level, and location reporting.

### Why Preserve Unknown Event Types

Telemetry schemas can evolve. Unknown events should not break ingestion or disappear. Keeping them in `telemetry_events` preserves history and allows future schema extensions without reprocessing raw files from scratch.

### Why Put Metrics in `analytics/`

Dashboard pages should not duplicate business logic. Centralizing metrics in `analytics/` gives one definition for cost, active users, error rates, tool success rates, and data quality metrics. This makes tests easier and keeps the dashboard focused on presentation.

### Why Use Dashboard-Ready Views

Views such as `v_daily_kpis`, `v_practice_kpis`, and `v_model_kpis` make dashboard queries predictable and reduce repeated SQL. They also create stable contracts between storage, analytics, and presentation.

### Why Include Data Quality as a First-Class Page

This dataset requires nested JSON parsing, employee joins, and type conversion. A visible data quality page makes ingestion issues observable and prevents misleading KPIs when source data changes.

### Why Keep the Architecture Local First

The current data volume is small enough for a local workflow, and the existing dependencies already include `duckdb`, `pandas`, `plotly`, `dash`, and `pytest`. A local-first architecture gets useful analytics quickly while keeping a clean path to later automation or scheduled refreshes.
