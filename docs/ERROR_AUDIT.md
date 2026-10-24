# Error Audit Report

## Overview
This document records all errors identified in the original notebook-based MCA Timetable Intelligent Assistant, their root causes, the fixes applied, and verification status.

---

## 1. DATA_SOURCE_NOT_FOUND — Excel Read Error

| Field | Value |
|-------|-------|
| **Error** | `[DATA_SOURCE_NOT_FOUND] Failed to find the data source: unsupported` |
| **Root Cause** | The notebook used `read_files()` with `format => 'excel'` to parse the timetable Excel file. The Excel data source may not be available on all Databricks runtimes. |
| **Fix** | The standalone app assumes the table `workspace.default.mca_timetable` already exists (created by running the notebook's data-loading cell once). The `execute_sql()` function in `src/sql_tool.py` uses Spark SQL or Databricks SQL connector instead of `read_files()`. |
| **Status** | \u2705 Fixed in standalone app |

## 2. No module named 'openai'

| Field | Value |
|-------|-------|
| **Error** | `ModuleNotFoundError: No module named 'openai'` |
| **Root Cause** | The notebook attempted to use the `openai` Python package for LLM calls, which was not installed in the Databricks runtime. |
| **Fix** | `src/llm_client.py` implements a graceful fallback chain: tries `openai` package first, then falls back to `requests`-based HTTP calls to the Databricks serving endpoint. The `requirements.txt` now includes `openai>=1.0.0` for standalone deployment. |
| **Status** | \u2705 Fixed |

## 3. Incorrect Answers to "What do I have today?" and "What time is Machine Learning?"

| Field | Value |
|-------|-------|
| **Error** | Agent returned incorrect or incomplete answers for common queries. |
| **Root Cause** | The `_find_subject()` function in the notebook used fuzzy matching that could match wrong subjects. The LLM sometimes hallucinated subjects not in the actual data. |
| **Fix** | 1. `src/sql_tool.py` uses stricter subject matching with `find_subject_in_question()`. 2. `src/agent.py` implements grounding checks — if the LLM answer is empty or suspiciously short, it falls back to directly formatted tool data. 3. The `_direct_tool_answer()` method provides a deterministic fallback without LLM. |
| **Status** | \u2705 Fixed |

## 4. Incorrect Faculty Responses

| Field | Value |
|-------|-------|
| **Error** | Faculty names were sometimes wrong or showed 'TBD' when faculty info existed. |
| **Root Cause** | Faculty lookup in the notebook relied on a partial name match against the Excel faculty details table, which could miss entries or match incorrectly. |
| **Fix** | `find_faculty_in_question()` in `src/sql_tool.py` queries the actual table for faculty names and uses exact + last-name matching. The formatter always shows 'TBD' when faculty is missing rather than inventing names. |
| **Status** | \u2705 Fixed |

## 5. Free-Period Output Showing '?' Instead of Times

| Field | Value |
|-------|-------|
| **Error** | Free period queries returned `?` instead of actual time strings. |
| **Root Cause** | The notebook's free-period code used `row.get('start_time')` which could return `None`, and the formatter didn't handle `None` properly. |
| **Fix** | `src/sql_tool.py` explicitly converts all time values to strings with `str(row.get('start_time', '') or '')`. `src/formatter.py` `format_free_periods()` computes duration from actual time strings and never outputs '?'. |
| **Status** | \u2705 Fixed |

## 6. Missing Support for Sections C and D

| Field | Value |
|-------|-------|
| **Error** | Sections C and D were not consistently handled. |
| **Root Cause** | The notebook's data parser included sections C and D in `MCA_SHEETS`, but the agent's default section was 'A' and the UI didn't offer C/D as options. |
| **Fix** | `app.py` sidebar offers all sections A, B, C, D. The SQL tool accepts any section value. No hardcoded section restrictions exist in the standalone code. |
| **Status** | \u2705 Fixed |

## 7. Missing Academic Track Filtering

| Field | Value |
|-------|-------|
| **Error** | Queries could return classes from wrong academic tracks (Cloud Computing vs Data Science vs Cyber Security). |
| **Root Cause** | The notebook's `query_timetable()` function did not filter by the `track` column. |
| **Fix** | `src/sql_tool.py` `query_timetable()` now accepts an optional `track` parameter and adds `track = '{track}'` to the WHERE clause. `app.py` sidebar includes a track dropdown. |
| **Status** | \u2705 Fixed |

## 8. Cross-Semester/Section Data Leakage

| Field | Value |
|-------|-------|
| **Error** | The notebook had an automatic cross-semester fallback that could return results from other sections when a subject query returned 0 results. |
| **Root Cause** | The `broad_sql` fallback in the notebook searched all semesters and sections when the primary query returned empty. |
| **Fix** | The cross-semester fallback has been **removed** entirely. All queries are strictly scoped to the specified semester and section. If no results found, the agent returns "No matching entries" rather than leaking other sections' data. |
| **Status** | \u2705 Fixed |

## 9. Weak Answer Grounding / Hallucination Prevention

| Field | Value |
|-------|-------|
| **Error** | The LLM could hallucinate subjects, faculty, or times not present in the tool results. |
| **Root Cause** | The notebook relied solely on the LLM to format the answer, without validating it against the actual tool data. |
| **Fix** | `src/agent.py` `_format_answer()` method checks: 1. If weekly query and tool results exist, reformats from raw data. 2. If LLM answer is empty or < 20 chars, falls back to tool-data formatting. 3. `filter_llm_reasoning()` removes reasoning blocks. |
| **Status** | \u2705 Fixed |

## 10. SQL Injection / Unsafe SQL Construction

| Field | Value |
|-------|-------|
| **Error** | The notebook used string interpolation for user input in SQL queries (e.g., `f"section = '{section}'"`). |
| **Root Cause** | No input sanitization was applied before interpolation. A malicious user could inject SQL via the question text or section parameter. |
| **Fix** | `src/sql_tool.py` `_sanitize()` function removes quotes, semicolons, SQL keywords (DROP, DELETE, INSERT, UPDATE, ALTER, CREATE, TRUNCATE, UNION), and enforces max length. All user-supplied values are sanitized before interpolation. `execute_sql()` validates that only SELECT queries are executed. |
| **Status** | \u2705 Fixed |

## 11. Hardcoded Personal Paths and Email

| Field | Value |
|-------|-------|
| **Error** | The notebook contained hardcoded paths like `/Workspace/Users/madhav.ptl026@gmail.com/...` and the Databricks host URL. |
| **Root Cause** | Personal workspace paths were embedded directly in the code. |
| **Fix** | All paths and hosts are now read from environment variables via `src/config.py`. The `.env.example` file documents required variables. No hardcoded paths exist in the standalone code. |
| **Status** | \u2705 Fixed |

## 12. Weekly Timetable Output Formatting

| Field | Value |
|-------|-------|
| **Error** | Weekly queries produced a single messy table with all days mixed together. |
| **Root Cause** | The notebook's formatter didn't split weekly results by day. |
| **Fix** | `src/formatter.py` `format_week_timetable()` groups entries by day and renders each day as a separate markdown table with its own header. Breaks/lunch are inserted for every day. |
| **Status** | \u2705 Fixed |
