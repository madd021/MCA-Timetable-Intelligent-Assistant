# Deployment Guide

## Prerequisites

1. A Databricks workspace with:
   - A SQL warehouse (for timetable queries)
   - A Foundation Model serving endpoint (e.g., `databricks-gpt-oss-120b`)
   - The `workspace.default.mca_timetable` table (created by running the notebook once)
2. A GitHub account with the repository cloned
3. Databricks CLI installed (`pip install databricks-cli`)

---

## Option 1: Databricks Apps (Recommended)

### Step 1: Prepare the timetable table

Run the original notebook's data-loading cell (Section 7) in your Databricks workspace to create `workspace.default.mca_timetable` from the Excel file.

### Step 2: Create the app

```bash
databricks apps create mca-timetable-assistant
```

Or via the Databricks UI:
1. Go to **Workspace > Apps**
2. Click **Create App**
3. Name: `mca-timetable-assistant`
4. Connect your GitHub repository: `madd021/MCA-Timetable-Intelligent-Assistant`
5. Branch: `main`

### Step 3: Configure environment variables

In the Databricks Apps UI or via CLI:

```bash
databricks apps update-env mca-timetable-assistant \
  --env DATABRICKS_HOST=https://your-workspace.cloud.databricks.com \
  --env DATABRICKS_TOKEN=your-token \
  --env DATABRICKS_WAREHOUSE_ID=your-warehouse-id \
  --env LLM_ENDPOINT=databricks-gpt-oss-120b \
  --env TIMETABLE_CATALOG=workspace \
  --env TIMETABLE_SCHEMA=default \
  --env TIMETABLE_TABLE=mca_timetable
```

> **Security:** Never commit tokens or credentials to the repository. Use Databricks Apps secret management.

### Step 4: Deploy

```bash
databricks apps deploy mca-timetable-assistant \
  --source-code-path . \
  --app-config-path app.yaml
```

### Step 5: Verify

The app will be available at: `https://your-workspace.cloud.databricks.com/apps/mca-timetable-assistant`

---

## Option 2: Local Development

### Step 1: Clone and install

```bash
git clone https://github.com/madd021/MCA-Timetable-Intelligent-Assistant.git
cd MCA-Timetable-Intelligent-Assistant
pip install -r requirements.txt
```

### Step 2: Configure environment

```bash
cp .env.example .env
# Edit .env with your Databricks credentials
```

### Step 3: Run

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

---

## Option 3: Databricks Notebook (Original)

The original notebook remains functional in the Databricks workspace. To use it:
1. Open the notebook in Databricks
2. Run all cells from top to bottom
3. Use the widget-based chatbot in Cell 24

The notebook uses the built-in Spark session and Databricks authentication — no environment variables needed.

---

## Configuration Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABRICKS_HOST` | Yes | — | Databricks workspace URL |
| `DATABRICKS_TOKEN` | Yes | — | Personal access token |
| `DATABRICKS_WAREHOUSE_ID` | Yes | — | SQL warehouse ID |
| `LLM_ENDPOINT` | No | `databricks-gpt-oss-120b` | LLM serving endpoint |
| `TIMETABLE_CATALOG` | No | `workspace` | UC catalog |
| `TIMETABLE_SCHEMA` | No | `default` | UC schema |
| `TIMETABLE_TABLE` | No | `mca_timetable` | Table name |

---

## Troubleshooting

### "No module named 'openai'"
Install dependencies: `pip install -r requirements.txt`

### "Only SELECT queries are allowed"
This is expected — the SQL tool only allows read-only queries.

### "databricks-sql-connector is required"
Install it: `pip install databricks-sql-connector`

### App shows "No matching timetable entries"
Ensure the `mca_timetable` table exists and has data. Run the notebook's data-loading cell first.
