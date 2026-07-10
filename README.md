# Claude Code Analytics

Executive analytics dashboard for Claude Code telemetry.

## Overview

Claude Code Analytics is an end-to-end analytics project that processes raw Claude Code telemetry logs into business insights.

The project implements a complete ETL pipeline:

- Load raw telemetry events from JSONL
- Load employee metadata from CSV
- Clean and normalize the data
- Validate datasets
- Store data in DuckDB
- Calculate business metrics
- Visualize KPIs with an interactive Dash dashboard

---

## Tech Stack

| Category | Technologies |
|----------|--------------|
| Language | Python 3.13 |
| Data Processing | Pandas |
| Database | DuckDB |
| Dashboard | Dash, Plotly |
| Testing | Pytest |
| Version Control | Git, GitHub |

---

## Project Structure

```text
claude-code-analytics/
│
├── analytics/        # Business metrics and SQL analytics
├── dashboard/        # Dash dashboard application
├── database/         # DuckDB connection, schema and repository
├── ingest/           # Data loading, cleaning and validation
├── tests/            # Unit tests
├── data/             # Input datasets (not included)
├── docs/             # Presentation
|
│
├── main.py           # ETL pipeline entry point
├── requirements.txt
├── README.md
├── AGENTS.md
├── LLM_USAGE.md
├── .env.example
└── .gitignore
```

---

## ETL Pipeline

```
Telemetry Logs (JSONL)
            │
            ▼
      Load Raw Data
            │
            ▼
      Data Cleaning
            │
            ▼
      Data Validation
            │
            ▼
        DuckDB Storage
            │
            ▼
     Business Analytics
            │
            ▼
      Executive Dashboard
```

---

## Dashboard Features

### Executive KPIs

- Total Users
- Total Sessions
- Total Events
- Total Cost (USD)
- Total Tokens

### Interactive Filters

- Date Range
- Practice
- Model

### Visualizations

- Requests per Day
- Token Usage by Model
- Cost by Practice
- Top Active Users
- Tool Usage Distribution

---

## Installation

Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/ClaudeCodeAnalytics.git
cd ClaudeCodeAnalytics
```

Create a virtual environment

```bash
python -m venv .venv
```

Activate it

Windows

```bash
.venv\Scripts\activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

## Running the ETL Pipeline

```bash
python main.py
```

This command will:

- load raw datasets
- clean and normalize data
- validate datasets
- create the DuckDB database
- save all processed data

---

## Running the Dashboard

```bash
python -m dashboard.app
```

Open your browser:

```
http://127.0.0.1:8050
```

---

## Data

The original telemetry dataset is **not included** in this repository because of its size.

Expected files:

```
data/
├── telemetry_logs.jsonl
└── employees.csv
```

---

## Screenshots

### Executive Overview

<img width="1679" height="771" alt="image" src="https://github.com/user-attachments/assets/9e890828-7e19-4590-83a5-a42b6fb2ff04" />

<img width="1773" height="551" alt="image" src="https://github.com/user-attachments/assets/4c67fdf8-4b0b-47de-8582-02e1413ce20c" />

<img width="881" height="529" alt="image" src="https://github.com/user-attachments/assets/05b3f5fe-24de-4bed-85e2-0e856702db4b" />

---

## Future Improvements

- Docker support
- Additional dashboard pages
- Export reports to CSV
- Automated ETL scheduling
- More advanced analytics
- Authentication


