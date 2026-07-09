# Data Analysis

## Scope

This document summarizes the initial exploration of:

- `data/telemetry_logs.jsonl`
- `data/employees.csv`

No implementation code is included here. The goal is to understand the data shape, identify important fields, and propose analytics and architecture for the project.

## Dataset Summary

| Dataset | Format | Size / Rows | Purpose |
| --- | --- | ---: | --- |
| `telemetry_logs.jsonl` | JSON Lines with nested CloudWatch-style log batches | 8,970 top-level rows, 49,379 flattened telemetry events | Claude Code usage, API, tool, prompt, and error telemetry |
| `employees.csv` | CSV | 30 employee records plus header | Employee dimension data for joining user telemetry to practice, level, and location |

The two datasets join cleanly by email:

- Telemetry users: 30 unique `attributes.user.email` values
- Employee records: 30 unique `email` values
- Telemetry users missing from employee file: 0
- Employees without telemetry: 0

## `telemetry_logs.jsonl`

### Structure

Each line is a JSON object representing a batch of log events. The top-level object has CloudWatch-like metadata:

- `messageType`
- `owner`
- `logGroup`
- `logStream`
- `subscriptionFilters`
- `logEvents`
- `year`
- `month`
- `day`

The important data is inside `logEvents`. Each `logEvents` item contains:

- `id`
- `timestamp`
- `message`

The `message` field is itself a JSON string. After parsing it, the inner event has:

- `body`: event body name, such as `claude_code.api_request`
- `attributes`: event-specific dimensions and metrics
- `scope`: telemetry library metadata
- `resource`: host, OS, service, and user-resource context

### Time Range and Volume

- Top-level JSONL rows: 8,970
- Flattened telemetry events: 49,379
- Date range: 2026-01-02 to 2026-02-01
- Unique users: 30
- Unique organizations: 30
- Unique sessions: 500

### Event Types

| Event name | Count | Meaning |
| --- | ---: | --- |
| `tool_decision` | 16,536 | Tool permission or decision events |
| `tool_result` | 16,191 | Tool execution result events |
| `api_request` | 12,781 | Model API calls with cost, token, model, and duration fields |
| `user_prompt` | 3,714 | User prompt events with redacted prompt text and prompt length |
| `api_error` | 157 | API error events with status and error details |

### Important Fields

Core identity and join fields:

- `attributes.user.email`: primary join key to `employees.csv`
- `attributes.user.id`: hashed or opaque user identifier
- `attributes.user.account_uuid`: account-level identifier
- `attributes.organization.id`: organization identifier
- `attributes.session.id`: session identifier

Time fields:

- `attributes.event.timestamp`: canonical event timestamp in ISO-8601 format
- `logEvents.timestamp`: outer log timestamp in epoch milliseconds
- Top-level `year`, `month`, `day`: partition fields

API request fields:

- `attributes.model`
- `attributes.cost_usd`
- `attributes.duration_ms`
- `attributes.input_tokens`
- `attributes.output_tokens`
- `attributes.cache_creation_tokens`
- `attributes.cache_read_tokens`

Prompt fields:

- `attributes.prompt`: redacted in this dataset as `<REDACTED>`
- `attributes.prompt_length`

Tool fields:

- `attributes.tool_name`
- `attributes.decision`
- `attributes.source`
- `attributes.decision_type`
- `attributes.decision_source`
- `attributes.success`
- `attributes.duration_ms`
- `attributes.tool_result_size_bytes`

Error fields:

- `attributes.status_code`
- `attributes.error`
- `attributes.attempt`

Environment fields:

- `attributes.terminal.type`
- `resource.host.arch`
- `resource.host.name`
- `resource.os.type`
- `resource.os.version`
- `resource.service.name`
- `resource.service.version`
- `resource.user.practice`
- `resource.user.profile`
- `resource.user.serial`

### Observed API Metrics

- API requests: 12,781
- Total cost: `$652.18`
- Average cost per API request: `$0.0510`
- Input tokens: 6,764,801
- Output tokens: 4,503,432
- Cache creation tokens: 51,586,251
- Cache read tokens: 642,138,562
- Average API duration: 8,987.1 ms
- API errors: 157
- API error rate versus API attempts: 1.21%

Model-level API request breakdown:

| Model | Requests | Cost | Avg duration ms | Input tokens | Output tokens | Cache read tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `claude-haiku-4-5-20251001` | 4,942 | `$20.11` | 5,547.2 | 5,116,872 | 638,244 | 51,014,481 |
| `claude-opus-4-5-20251101` | 2,563 | `$235.27` | 11,333.4 | 285,349 | 1,165,879 | 203,125,445 |
| `claude-opus-4-6` | 2,883 | `$226.75` | 10,459.4 | 1,036,105 | 1,361,355 | 217,764,748 |
| `claude-sonnet-4-5-20250929` | 2,122 | `$149.47` | 11,889.5 | 270,957 | 1,205,778 | 151,244,072 |
| `claude-sonnet-4-6` | 271 | `$20.58` | 11,137.7 | 55,518 | 132,176 | 18,989,816 |

Practice-level API request breakdown:

| Practice | API requests | User prompts | Cost |
| --- | ---: | ---: | ---: |
| Backend Engineering | 1,467 | 436 | `$73.42` |
| Data Engineering | 3,618 | 1,035 | `$184.94` |
| Frontend Engineering | 4,108 | 1,211 | `$209.81` |
| ML Engineering | 2,800 | 782 | `$141.25` |
| Platform Engineering | 788 | 250 | `$42.77` |

### Observed Tool Metrics

- Tool results: 16,191
- Tool success rate: 97.03%
- Average tool duration: 12,856.6 ms

Most common tools:

| Tool | Events |
| --- | ---: |
| `Read` | 10,070 |
| `Bash` | 9,233 |
| `Edit` | 4,127 |
| `Grep` | 2,416 |
| `Glob` | 1,527 |
| `mcp_tool` | 1,323 |
| `Write` | 933 |
| `TodoWrite` | 830 |
| `Task` | 654 |
| `TaskUpdate` | 636 |

### Error Patterns

Status code counts:

| Status | Count |
| --- | ---: |
| `undefined` | 79 |
| `429` | 38 |
| `400` | 29 |
| `500` | 9 |
| `401` | 2 |

Top observed error messages:

| Error | Count |
| --- | ---: |
| `Request was aborted.` | 75 |
| `This request would exceed your account's rate limit. Please try again later.` | 38 |
| `output_config: Extra inputs are not permitted` | 13 |
| `tools: Tool names must be unique.` | 12 |
| `Internal server error` | 9 |
| `Could not load credentials from any providers` | 4 |
| `400 The provided request is not valid` | 4 |
| `OAuth token has expired. Please obtain a new token or refresh your existing token.` | 2 |

### Terminal and Practice Distribution

Terminal types:

| Terminal | Events |
| --- | ---: |
| `vscode` | 21,193 |
| `pycharm` | 11,901 |
| `webstorm` | 5,318 |
| `Terminal` | 3,029 |
| `WarpTerminal` | 2,955 |
| `cursor` | 2,006 |
| `intellij` | 1,582 |
| `iTerm2` | 1,395 |

Telemetry events by `resource.user.practice`:

| Practice | Events |
| --- | ---: |
| Frontend Engineering | 15,859 |
| Data Engineering | 13,913 |
| ML Engineering | 10,824 |
| Backend Engineering | 5,643 |
| Platform Engineering | 3,140 |

## `employees.csv`

### Structure

The CSV contains one row per employee with these columns:

- `email`
- `full_name`
- `practice`
- `level`
- `location`

Example row shape:

```text
email,full_name,practice,level,location
reese.garcia@example.com,Reese Garcia,Frontend Engineering,L5,Poland
```

### Important Fields

- `email`: primary key and join key to telemetry `attributes.user.email`
- `full_name`: human-readable employee label for dashboards
- `practice`: organization/team dimension
- `level`: career level dimension, formatted as `L1` through `L10`
- `location`: geographic dimension

### Distribution

Employees by practice:

| Practice | Employees |
| --- | ---: |
| Backend Engineering | 5 |
| Data Engineering | 7 |
| Frontend Engineering | 10 |
| ML Engineering | 6 |
| Platform Engineering | 2 |

Employees by level:

| Level | Employees |
| --- | ---: |
| L1 | 2 |
| L2 | 3 |
| L3 | 5 |
| L4 | 7 |
| L5 | 5 |
| L6 | 1 |
| L7 | 4 |
| L8 | 1 |
| L9 | 1 |
| L10 | 1 |

Employees by location:

| Location | Employees |
| --- | ---: |
| Poland | 10 |
| Canada | 7 |
| Germany | 6 |
| United Kingdom | 5 |
| United States | 2 |

## Suggested Analytics and KPIs

### Adoption and Engagement

- Active users per day, week, and month
- Active users by practice, level, and location
- Sessions per user
- Prompts per user and prompts per session
- API requests per prompt
- Tool calls per prompt
- Usage by terminal type or IDE

### Cost Management

- Total cost by day, user, practice, model, and terminal
- Cost per active user
- Cost per prompt
- Cost per session
- Cost per 1,000 output tokens
- Cost by model mix
- High-cost users, sessions, or prompts for review
- Cache read and cache creation token trends
- Estimated cache savings or cache efficiency ratio

### Productivity and Workflow

- Tool usage mix by practice and level
- Tool success rate overall and by tool
- Average tool duration by tool
- Tool result size by tool
- Share of accepted versus rejected tool decisions
- Most common tool chains within a session
- Session depth: prompts, API calls, and tool calls per session

### Reliability

- API error rate by day, model, terminal, and practice
- Error counts by status code
- Rate limit events by user, organization, and time window
- Tool failure rate by tool
- Slow API request rate, for example requests over 30 seconds
- Slow tool execution rate
- Retry or attempt patterns where `attributes.attempt` is present

### Organizational Reporting

- Practice-level usage intensity: events or cost per employee
- Level-level usage: adoption by seniority
- Location-level usage and cost
- User leaderboard for prompts, sessions, tool usage, and spend
- Model adoption by practice
- IDE or terminal adoption by practice

### Data Quality KPIs

- Percentage of telemetry events with joinable employee records
- Missing or malformed timestamps
- Missing cost or token fields on `api_request` events
- Missing success flags on `tool_result` events
- Duplicate log event IDs
- Difference between outer `logEvents.timestamp` and inner `attributes.event.timestamp`

## Proposed Architecture

The project already has a small structure with `ingest`, `analytics`, `dashboard`, `database`, `docs`, and `tests` directories. A practical architecture should preserve that separation.

### 1. Ingestion Layer

Responsibility:

- Read `telemetry_logs.jsonl` as streaming JSONL, not all at once.
- Parse each top-level batch.
- Flatten each `logEvents` item.
- Parse the nested `message` JSON string.
- Read `employees.csv`.
- Validate required fields and data types.

Suggested outputs:

- Raw top-level log batch table
- Flattened telemetry event table
- Employee dimension table
- Data quality report

Existing fit:

- `ingest/loader.py`
- `ingest/cleaner.py`
- `ingest/validator.py`

### 2. Normalization Layer

Responsibility:

- Convert string metrics into numeric types.
- Convert timestamps into timezone-aware datetimes.
- Normalize event names and field names.
- Split nested telemetry into consistent tables.
- Preserve raw event payloads for auditability.

Suggested logical tables:

- `employees`
- `telemetry_events`
- `api_requests`
- `api_errors`
- `user_prompts`
- `tool_decisions`
- `tool_results`
- `sessions`

### 3. Storage Layer

For this project size, a local analytical database is enough.

Recommended options:

- SQLite for simple persistence and broad compatibility.
- DuckDB if analytics performance and direct file querying become important.

Suggested location:

- `database/`

Storage should support:

- Incremental reloads or full refreshes
- Primary keys on log event ID where possible
- Indexes on timestamp, user email, session ID, event name, model, and practice

### 4. Analytics Layer

Responsibility:

- Compute reusable metrics and KPI tables.
- Join telemetry to employee dimensions.
- Produce model, user, practice, level, location, terminal, and session aggregations.

Suggested modules:

- Cost analytics
- Token analytics
- Tool analytics
- Prompt and session analytics
- Reliability analytics
- Data quality analytics

Suggested location:

- `analytics/`

### 5. Dashboard Layer

Responsibility:

- Present high-level KPIs and drilldowns.
- Support filters for date range, practice, level, location, model, user, and terminal.

Suggested views:

- Executive overview: total cost, users, prompts, sessions, error rate
- Cost and model usage
- Team and employee adoption
- Tool usage and success
- Reliability and errors
- Data quality

Suggested location:

- `dashboard/`

### 6. Testing and Validation

Responsibility:

- Verify parsing of nested JSON messages.
- Verify employee join completeness.
- Verify type conversion for costs, tokens, durations, timestamps, and booleans.
- Verify metric calculations on small fixtures.
- Verify handling of malformed or incomplete rows.

Suggested location:

- `tests/`

## Initial Data Model

### `employees`

One row per employee.

Key fields:

- `email`
- `full_name`
- `practice`
- `level`
- `location`

### `telemetry_events`

One row per flattened telemetry event.

Key fields:

- `event_id`
- `event_timestamp`
- `event_name`
- `body`
- `user_email`
- `user_id`
- `account_uuid`
- `organization_id`
- `session_id`
- `terminal_type`
- `service_version`
- `host_name`
- `os_type`
- `raw_message`

### `api_requests`

One row per `api_request` event.

Key fields:

- `event_id`
- `event_timestamp`
- `user_email`
- `session_id`
- `model`
- `cost_usd`
- `duration_ms`
- `input_tokens`
- `output_tokens`
- `cache_creation_tokens`
- `cache_read_tokens`

### `tool_results`

One row per `tool_result` event.

Key fields:

- `event_id`
- `event_timestamp`
- `user_email`
- `session_id`
- `tool_name`
- `success`
- `duration_ms`
- `tool_result_size_bytes`
- `decision_type`
- `decision_source`

### `tool_decisions`

One row per `tool_decision` event.

Key fields:

- `event_id`
- `event_timestamp`
- `user_email`
- `session_id`
- `tool_name`
- `decision`
- `source`

### `user_prompts`

One row per `user_prompt` event.

Key fields:

- `event_id`
- `event_timestamp`
- `user_email`
- `session_id`
- `prompt_length`
- `prompt_redacted`

### `api_errors`

One row per `api_error` event.

Key fields:

- `event_id`
- `event_timestamp`
- `user_email`
- `session_id`
- `model`
- `status_code`
- `error`
- `attempt`

## Data Quality Notes

- The telemetry file requires two-stage parsing: JSONL row first, then nested JSON from `logEvents.message`.
- Prompt text is redacted, so content analytics should use `prompt_length` and event timing only.
- Cost, token, duration, and boolean fields are encoded as strings inside `attributes` and should be typed during normalization.
- `resource.user.email` is empty in observed samples; use `attributes.user.email` as the join key.
- Top-level `year`, `month`, and `day` match partitioning intent, but event timestamp should be the source of truth for analytics.
- Some `api_error` events have `status_code` as `undefined`; error reporting should group this explicitly.
- The dataset has complete employee join coverage, which makes team, level, and location reporting reliable for this sample.
