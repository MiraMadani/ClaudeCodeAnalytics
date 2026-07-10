# AGENTS.md

# Agent Configuration

## Agent

**Tool:** OpenAI Codex CLI

The project was developed using Codex CLI as an AI-assisted coding agent.

## Purpose

The agent was configured to assist with:

- project structure generation;
- ETL pipeline implementation;
- DuckDB schema creation;
- SQL analytics queries;
- Dash dashboard components;
- repository organization;
- documentation generation;
- code refactoring.

## Development Workflow

During development, the agent was used iteratively.

Typical workflow:

1. Analyze the requirement.
2. Generate an implementation proposal.
3. Review the generated code.
4. Adapt and modify the implementation when necessary.
5. Test the functionality locally.
6. Repeat until the feature was complete.

All generated code was manually reviewed before being included in the project.

## Dataset Knowledge

The agent was instructed to work with two datasets:

- `telemetry_logs.jsonl` – Claude Code telemetry events
- `employees.csv` – employee metadata

The agent understood that telemetry events must be:

- parsed from JSONL;
- flattened into tabular format;
- cleaned and validated;
- stored in DuckDB;
- analyzed through SQL queries;
- visualized in Dash.

## Generated Components

The agent assisted in generating:

- ETL pipeline
- data loading
- data cleaning
- validation helpers
- DuckDB schema
- repository layer
- analytics queries
- dashboard layout
- callbacks
- Plotly charts
- README draft

## Human Responsibilities

The project owner was responsible for:

- reviewing generated code;
- validating business logic;
- fixing integration issues;
- testing the application;
- organizing the repository;
- making architectural decisions.

## Reproducibility

Install dependencies:

```bash
pip install -r requirements.txt
```

Run ETL:

```bash
python main.py
```

Run dashboard:

```bash
python -m dashboard.app
```
