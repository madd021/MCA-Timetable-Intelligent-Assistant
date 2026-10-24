# MCA Timetable Intelligent Assistant

An AI-powered chatbot that answers natural-language questions about the MCA Department class timetable. Built as a single tool-calling agent on Databricks, with a Streamlit web interface for deployment.

## Features

- \U0001f4ac **Natural Language Q&A** — Ask about classes, faculty, rooms, days, and times in plain English
- \U0001f50d **Smart Query Engine** — SQL-backed tool with intent detection for today/tomorrow, next/previous class, free periods, conflicts, week view
- \u2615 **Breaks & Lunch** — Fixed break slots (10:40-10:50, 12:50-13:20, 15:20-15:30) always displayed in output
- \U0001f5d3\ufe0f **Clean Week View** — Weekly timetable rendered as per-day tables with breaks
- \u2697\ufe0f **Lab Detection** — Lab sessions visually marked with emoji
- \u26a0\ufe0f **Conflict Detection** — Identifies overlapping classes for the same section
- \U0001f9e0 **Conversation Memory** — Follow-up questions resolved using context (e.g., "Where?" → "Where is [last subject]?")
- \U0001f6e1\ufe0f **Guardrails** — Non-timetable questions are politely blocked
- \U0001f512 **SQL Safety** — Input sanitization, SELECT-only queries, no injection
- \U0001f4ca **Track Filtering** — Filter by Cloud Computing, Data Science, or Cyber Security tracks

## Technology Stack

| Component | Technology |
|-----------|-----------|
| LLM | Databricks Foundation Model API (`databricks-gpt-oss-120b`) |
| Data Storage | Databricks Unity Catalog (`workspace.default.mca_timetable`) |
| Web Framework | Streamlit |
| SQL Access | Databricks SQL Connector / Spark SQL |
| Platform | Databricks Apps |
| Language | Python 3.9+ |

## Project Structure

```
MCA-Timetable-Intelligent-Assistant/
\u2502\u2500\u2500 app.py              # Streamlit web application
\u2502\u2500\u2500 app.yaml            # Databricks Apps configuration
\u2502\u2500\u2500 requirements.txt     # Python dependencies
\u2502\u2500\u2500 .env.example        # Environment variable template
\u2502\u2500\u2500 .gitignore
\u2502\u2500\u2500 src/
\u2502   \u2502\u2500\u2500 config.py        # Configuration from env vars
\u2502   \u2502\u2500\u2500 sql_tool.py      # Safe SQL query tool
\u2502   \u2502\u2500\u2500 memory.py        # Conversation memory
\u2502   \u2502\u2500\u2500 llm_client.py     # LLM client (openai/requests fallback)
\u2502   \u2502\u2500\u2500 formatter.py      # Answer formatting (breaks, week tables)
\u2502   \u2502\u2500\u2500 agent.py         # MCATimetableAgent class
\u2502   \u2500\u2500\u2500 __init__.py
\u2502\u2500\u2500 tests/
\u2502   \u2502\u2500\u2500 test_formatter.py   # Formatter unit tests
\u2502   \u2502\u2500\u2500 test_sql_tool.py    # SQL tool unit tests
\u2502   \u2500\u2500\u2500 __init__.py
\u2502\u2500\u2500 docs/
\u2502   \u2502\u2500\u2500 ERROR_AUDIT.md     # Error audit report
\u2502   \u2502\u2500\u2500 TEST_REPORT.md     # Test results
\u2502   \u2500\u2500\u2500 DEPLOYMENT.md     # Deployment guide
\u2500\u2500\u2500 README.md
```

## Installation

### Prerequisites
- Python 3.9+
- A Databricks workspace with:
  - A SQL warehouse
  - A Foundation Model serving endpoint
  - The `workspace.default.mca_timetable` table (run the original notebook's data-loading cell once)

### Setup

```bash
git clone https://github.com/madd021/MCA-Timetable-Intelligent-Assistant.git
cd MCA-Timetable-Intelligent-Assistant
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Databricks credentials
```

## Running Locally

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABRICKS_HOST` | Yes | Databricks workspace URL |
| `DATABRICKS_TOKEN` | Yes | Personal access token |
| `DATABRICKS_WAREHOUSE_ID` | Yes | SQL warehouse ID |
| `LLM_ENDPOINT` | No | LLM endpoint (default: `databricks-gpt-oss-120b`) |
| `TIMETABLE_CATALOG` | No | UC catalog (default: `workspace`) |
| `TIMETABLE_SCHEMA` | No | UC schema (default: `default`) |
| `TIMETABLE_TABLE` | No | Table name (default: `mca_timetable`) |

## Testing

```bash
# Syntax check
python -m compileall src/ tests/ app.py

# Run unit tests
python -m pytest tests/ -v
```

See [docs/TEST_REPORT.md](docs/TEST_REPORT.md) for detailed test results.

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for Databricks Apps deployment instructions.

## Known Limitations

- Requires the `mca_timetable` table to exist in Databricks Unity Catalog
- LLM endpoint must be deployed and ready in the Databricks workspace
- The Streamlit app needs network access to Databricks APIs
- Timetable data is static — updated by re-running the notebook's Excel parser

## Error Audit

See [docs/ERROR_AUDIT.md](docs/ERROR_AUDIT.md) for the full list of fixed issues.
