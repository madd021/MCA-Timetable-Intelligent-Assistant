# Test Report

## Test Environment

- **Platform:** Databricks Serverless Compute
- **Python:** 3.12
- **Test Framework:** Manual test runner (pytest-compatible test classes)
- **Date:** 2026-10-24

---

## 1. Syntax Check (compileall equivalent)

**Command:** `python -c "import ast; ..."` (AST parse all .py files)

**Result:** All 11 Python files pass syntax check.

| File | Status |
|------|--------|
| `app.py` | PASS |
| `src/__init__.py` | PASS |
| `src/config.py` | PASS |
| `src/sql_tool.py` | PASS |
| `src/memory.py` | PASS |
| `src/formatter.py` | PASS |
| `src/llm_client.py` | PASS |
| `src/agent.py` | PASS |
| `tests/__init__.py` | PASS |
| `tests/test_formatter.py` | PASS |
| `tests/test_sql_tool.py` | PASS |

---

## 2. Unit Tests

**Command:** `python -m pytest tests/ -v` (equivalent)

**Result:** 39/40 tests passed initially. 1 guardrail test failed — fixed by implementing hard-block vs soft-block in guardrail. After fix: **40/40 passed**.

### Formatter Tests (14 tests)

| Test | Status |
|------|--------|
| `TestFormatDayTable.test_empty_entries` | PASS |
| `TestFormatDayTable.test_single_entry` | PASS |
| `TestFormatDayTable.test_breaks_inserted` | PASS |
| `TestFormatDayTable.test_lab_marked` | PASS |
| `TestFormatWeekTimetable.test_empty` | PASS |
| `TestFormatWeekTimetable.test_multiple_days` | PASS |
| `TestFormatWeekTimetable.test_breaks_in_week` | PASS |
| `TestFormatFreePeriods.test_empty` | PASS |
| `TestFormatFreePeriods.test_no_question_marks` | PASS |
| `TestFormatConflicts.test_no_conflicts` | PASS |
| `TestFormatConflicts.test_with_conflicts` | PASS |
| `TestFilterLLMReasoning.test_removes_reasoning` | PASS |
| `TestInsertBreaks.test_inserts_all_breaks` | PASS |
| `TestInsertBreaks.test_no_duplicate_breaks` | PASS |

### SQL Tool Tests (26 tests)

| Test | Status |
|------|--------|
| `TestSanitize.test_removes_quotes` | PASS |
| `TestSanitize.test_removes_semicolons` | PASS |
| `TestSanitize.test_removes_drop` | PASS |
| `TestSanitize.test_removes_union` | PASS |
| `TestSanitize.test_max_length` | PASS |
| `TestSanitize.test_empty` | PASS |
| `TestParseTimeExpr.test_morning` | PASS |
| `TestParseTimeExpr.test_afternoon` | PASS |
| `TestParseTimeExpr.test_before_time` | PASS |
| `TestParseTimeExpr.test_after_time` | PASS |
| `TestParseTimeExpr.test_no_time` | PASS |
| `TestResolveDay.test_today` | PASS |
| `TestResolveDay.test_tomorrow` | PASS |
| `TestResolveDay.test_monday` | PASS |
| `TestResolveDay.test_wednesday` | PASS |
| `TestResolveDay.test_no_day` | PASS |
| `TestQueryTypeDetection.test_week_query` | PASS |
| `TestQueryTypeDetection.test_lab_query` | PASS |
| `TestQueryTypeDetection.test_conflict_query` | PASS |
| `TestQueryTypeDetection.test_next_class` | PASS |
| `TestQueryTypeDetection.test_free_period` | PASS |
| `TestQueryTypeDetection.test_count_query` | PASS |
| `TestQueryTypeDetection.test_break_query` | PASS |
| `TestGuardrail.test_timetable_allowed` | PASS |
| `TestGuardrail.test_non_timetable_blocked` | PASS (after fix) |
| `TestGuardrail.test_empty_blocked` | PASS |

---

## 3. Integration Tests (Skipped)

The following tests require a live Databricks connection and were not executed:

- Timetable query execution against `workspace.default.mca_timetable`
- LLM tool-calling loop with `databricks-gpt-oss-120b`
- Streamlit app startup (`streamlit run app.py`)
- End-to-end agent Q&A tests

**To run integration tests:**
1. Set environment variables (see `.env.example`)
2. Run the original notebook to create the `mca_timetable` table
3. Run: `python -m streamlit run app.py`

---

## 4. Test Summary

| Category | Tests | Passed | Failed | Skipped |
|----------|-------|--------|--------|---------|
| Syntax Check | 11 | 11 | 0 | 0 |
| Formatter | 14 | 14 | 0 | 0 |
| SQL Tool | 26 | 26 | 0 | 0 |
| Integration | — | — | — | All |
| **Total** | **51** | **51** | **0** | — |
