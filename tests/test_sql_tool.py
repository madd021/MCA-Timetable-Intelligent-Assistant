"""
Tests for the SQL tool module.
Tests SQL safety, input sanitization, and query-type detection.
Does not require a live Databricks connection.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.sql_tool import (
    _sanitize, _parse_time_expr, _resolve_day, _is_week_query,
    _is_lab_query, _is_conflict_query, _is_next_class_query,
    _is_free_period_query, _is_count_query, _is_break_query,
)


class TestSanitize:
    def test_removes_quotes(self):
        assert "'" not in _sanitize("hello'world")
    
    def test_removes_semicolons(self):
        assert ";" not in _sanitize("hello;world")
    
    def test_removes_drop(self):
        result = _sanitize("DROP TABLE students")
        assert "DROP" not in result.upper()
    
    def test_removes_union(self):
        result = _sanitize("UNION SELECT password")
        assert "UNION" not in result.upper()
    
    def test_max_length(self):
        result = _sanitize("x" * 500, max_len=50)
        assert len(result) <= 50
    
    def test_empty(self):
        assert _sanitize("") == ""
        assert _sanitize(None) == ""


class TestParseTimeExpr:
    def test_morning(self):
        result = _parse_time_expr("What classes do I have in the morning?")
        assert result == ("06:00", "12:00")
    
    def test_afternoon(self):
        result = _parse_time_expr("Any classes in the afternoon?")
        assert result == ("12:00", "17:00")
    
    def test_before_time(self):
        result = _parse_time_expr("classes before 2pm")
        assert result is not None
        assert result[1] == "14:00"
    
    def test_after_time(self):
        result = _parse_time_expr("classes after 3pm")
        assert result is not None
        assert result[0] == "15:00"
    
    def test_no_time(self):
        result = _parse_time_expr("What is my schedule?")
        assert result is None


class TestResolveDay:
    def test_today(self):
        from datetime import datetime
        result = _resolve_day("What do I have today?")
        assert result == datetime.now().strftime("%A")
    
    def test_tomorrow(self):
        from datetime import datetime, timedelta
        result = _resolve_day("What about tomorrow?")
        assert result == (datetime.now() + timedelta(days=1)).strftime("%A")
    
    def test_monday(self):
        assert _resolve_day("What is my Monday schedule?") == "Monday"
    
    def test_wednesday(self):
        assert _resolve_day("Any free periods on wed?") == "Wednesday"
    
    def test_no_day(self):
        assert _resolve_day("What is optimization technique?") is None


class TestQueryTypeDetection:
    def test_week_query(self):
        assert _is_week_query("Show my full week timetable")
        assert _is_week_query("What is my weekly schedule?")
        assert not _is_week_query("What do I have today?")
    
    def test_lab_query(self):
        assert _is_lab_query("Do I have a lab today?")
        assert not _is_lab_query("What classes do I have?")
    
    def test_conflict_query(self):
        assert _is_conflict_query("Are there any conflicts?")
        assert _is_conflict_query("Any overlapping classes?")
    
    def test_next_class(self):
        assert _is_next_class_query("What is my next class?")
    
    def test_free_period(self):
        assert _is_free_period_query("Any free periods?")
        assert _is_free_period_query("Do I have any free slots?")
    
    def test_count_query(self):
        assert _is_count_query("How many classes today?")
    
    def test_break_query(self):
        assert _is_break_query("When is break?")
        assert _is_break_query("When is lunch?")
        assert not _is_break_query("What is Java?")


class TestGuardrail:
    def test_timetable_allowed(self):
        from src.llm_client import guardrail_check
        allowed, _ = guardrail_check("What classes do I have today?")
        assert allowed
    
    def test_non_timetable_blocked(self):
        from src.llm_client import guardrail_check
        allowed, _ = guardrail_check("What is the weather today?")
        assert not allowed
    
    def test_empty_blocked(self):
        from src.llm_client import guardrail_check
        allowed, _ = guardrail_check("")
        assert not allowed
