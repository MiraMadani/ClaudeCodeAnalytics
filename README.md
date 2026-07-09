Claude Code Analytics

Executive analytics dashboard for Claude Code telemetry logs.

Overview

Claude Code Analytics is an ETL and analytics project built with Python, DuckDB, and Dash.

The application:

loads telemetry events from JSONL files;
loads employee metadata from CSV;
cleans and validates the data;
stores the data in DuckDB;
calculates business metrics;
displays an interactive executive dashboard.
Tech Stack
Python 3.13
Pandas
DuckDB
Dash
Plotly
Pytest
Project Structure
analytics/      Business metrics and SQL queries
dashboard/      Dash application
database/       DuckDB schema and repository
etl/            Loading, cleaning and validation
data/           Input datasets (not included)
tests/          Unit tests
main.py         ETL pipeline
Dashboard Features

Executive Overview includes:

Total Users
Total Sessions
Total Events
Total Cost
Total Tokens

Interactive filters:

Date range
Practice
Model

Visualizations:

Requests per Day
Token Usage by Model
Cost by Practice
Top Active Users
Tool Usage Distribution
Installation
git clone https://github.com/MiraMadani/ClaudeCodeAnalytics.git

cd ClaudeCodeAnalytics

python -m venv .venv

.venv\Scripts\activate

pip install -r requirements.txt
Run ETL
python main.py

This loads the source datasets, performs cleaning and validation, and stores the results in DuckDB.

Run Dashboard
python -m dashboard.app

Then open

http://127.0.0.1:8050
Data

The original telemetry dataset is not included because of its size.

Expected files:

data/
    telemetry_logs.jsonl
    employees.csv
Architecture
JSONL + CSV
      │
      ▼
Loading
      │
      ▼
Cleaning
      │
      ▼
Validation
      │
      ▼
DuckDB
      │
      ▼
Analytics
      │
      ▼
Dash Dashboard
Screenshots

Add dashboard screenshots here after running the application.

Future Improvements
Docker support
Additional dashboard pages
Export to CSV
Authentication
More analytics and drill-down reports
