"""
Tests for the formatter module.
These tests don't require a Databricks connection — they test pure formatting logic.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.formatter import (
    format_day_table, format_week_timetable, format_free_periods,
    format_count_result, format_single_class, format_conflicts,
    filter_llm_reasoning, _insert_breaks,
)
from src.config import FIXED_BREAKS


class TestFormatDayTable:
    def test_empty_entries(self):
        result = format_day_table([], "Monday")
        assert "Monday" in result
        assert "No classes" in result
    
    def test_single_entry(self):
        entries = [{"day": "Tuesday", "start_time": "09:40", "end_time": "10:40", "subject": "Java", "faculty": "Dr. Smith", "room": "N 808", "is_lab": False, "is_break": False}]
        result = format_day_table(entries, "Tuesday")
        assert "Tuesday" in result
        assert "09:40" in result
        assert "Java" in result
        assert "Dr. Smith" in result
    
    def test_breaks_inserted(self):
        entries = [{"day": "Monday", "start_time": "09:40", "end_time": "10:40", "subject": "Math", "faculty": "Prof. X", "room": "N 714", "is_lab": False, "is_break": False}]
        result = format_day_table(entries, "Monday")
        # Should contain all 3 fixed breaks
        for brk in FIXED_BREAKS:
            assert brk["start"] in result, f"Break at {brk['start']} should be in output"
    
    def test_lab_marked(self):
        entries = [{"day": "Monday", "start_time": "13:20", "end_time": "14:20", "subject": "Java Lab", "faculty": "Dr. X", "room": "N 808", "is_lab": True, "is_break": False}]
        result = format_day_table(entries, "Monday")
        assert "\u2697" in result  # lab emoji


class TestFormatWeekTimetable:
    def test_empty(self):
        result = format_week_timetable([])
        assert "No classes" in result
    
    def test_multiple_days(self):
        entries = [
            {"day": "Monday", "start_time": "09:40", "end_time": "10:40", "subject": "Math", "faculty": "Prof. X", "room": "N 714", "is_lab": False, "is_break": False},
            {"day": "Tuesday", "start_time": "10:50", "end_time": "11:50", "subject": "Java", "faculty": "Dr. Y", "room": "N 808", "is_lab": False, "is_break": False},
        ]
        result = format_week_timetable(entries)
        assert "Monday" in result
        assert "Tuesday" in result
        # Each day should have its own table header
        assert result.count("| Time |") >= 2
    
    def test_breaks_in_week(self):
        entries = [
            {"day": "Monday", "start_time": "09:40", "end_time": "10:40", "subject": "Math", "faculty": "Prof. X", "room": "N 714", "is_lab": False, "is_break": False},
            {"day": "Wednesday", "start_time": "09:40", "end_time": "10:40", "subject": "Java", "faculty": "Dr. Y", "room": "N 808", "is_lab": False, "is_break": False},
        ]
        result = format_week_timetable(entries)
        # Each day should have breaks
        for brk in FIXED_BREAKS:
            assert brk["start"] in result


class TestFormatFreePeriods:
    def test_no_question_marks(self):
        """Free period output should never contain '?' for times."""
        entries = [{"free_from": "09:00", "free_until": "09:40", "day": "Monday"}]
        result = format_free_periods(entries, "Monday")
        assert "?" not in result
        assert "09:00" in result
        assert "09:40" in result
    
    def test_empty(self):
        result = format_free_periods([])
        assert "No free periods" in result


class TestFormatConflicts:
    def test_no_conflicts(self):
        result = format_conflicts([])
        assert "No timetable conflicts" in result
    
    def test_with_conflicts(self):
        entries = [{"day": "Monday", "subject": "CONFLICT: Math vs Java", "faculty": "X / Y", "room": "N 714 / N 808"}]
        result = format_conflicts(entries)
        assert "CONFLICT" in result
        assert "Monday" in result


class TestFilterLLMReasoning:
    def test_removes_reasoning(self):
        text = "Hello {type: reasoning, thought: blah} World"
        result = filter_llm_reasoning(text)
        assert "reasoning" not in result
        assert "Hello" in result
        assert "World" in result


class TestInsertBreaks:
    def test_inserts_all_breaks(self):
        entries = [{"day": "Monday", "start_time": "09:40", "end_time": "10:40", "subject": "Math", "is_break": False}]
        result = _insert_breaks(entries)
        assert len(result) == 4  # 1 class + 3 breaks
    
    def test_no_duplicate_breaks(self):
        entries = [
            {"day": "Monday", "start_time": "09:40", "end_time": "10:40", "subject": "Math", "is_break": False},
            {"day": "Monday", "start_time": "10:40", "end_time": "10:50", "subject": "\u2615 Short Break", "is_break": True},
        ]
        result = _insert_breaks(entries)
        # Should not add another break at 10:40
        count_1040 = sum(1 for e in result if e.get("start_time") == "10:40")
        assert count_1040 == 1
