"""
Answer formatter: produces clean per-day tables for weekly queries,
inserts fixed break/lunch slots, and marks labs/conflicts.

FIXES ADDRESSED (vs notebook version):
  - Weekly output: split by day, each rendered as a distinct aligned table
  - Breaks/lunch: always inserted at fixed time slots for every day
  - Labs: marked with \u2697\ufe0f emoji for visual clarity
  - Conflicts: marked with \u26a0\ufe0f warning emoji
  - Free periods: show actual time strings, never '?'
"""
import re
from typing import List, Dict, Any
from .config import DAYS, FIXED_BREAKS


def _insert_breaks(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Insert fixed break entries into a sorted list of class entries."""
    if not entries:
        return entries
    
    result = list(entries)
    for brk in FIXED_BREAKS:
        # Check if a break at this time already exists
        already = any(
            e.get('start_time', '') == brk['start'] or 
            (e.get('is_break') and brk['start'] in str(e.get('start_time', '')))
            for e in result
        )
        if not already:
            break_entry = {
                'day': result[0].get('day', '') if result else '',
                'start_time': brk['start'],
                'end_time': brk['end'],
                'subject': brk['label'],
                'faculty': '',
                'room': '',
                'semester': result[0].get('semester', 0) if result else 0,
                'section': result[0].get('section', '') if result else '',
                'is_break': True,
                'is_lab': False,
                'track': '',
            }
            result.append(break_entry)
    
    # Sort by start_time
    result.sort(key=lambda x: x.get('start_time', '00:00'))
    return result


def format_day_table(entries: List[Dict[str, Any]], day_name: str = None) -> str:
    """Format a single day's entries as a clean markdown table."""
    if not entries:
        day_label = day_name or "No entries"
        return f"**{day_label}**\n\n_No classes scheduled_\n"
    
    entries = _insert_breaks(entries)
    day_label = day_name or entries[0].get('day', 'Today')
    
    lines = [f"**{day_label}**", "", 
             "| Time | Subject | Faculty | Room |", 
             "|------|---------|---------|------|"]
    
    for e in entries:
        time_slot = f"{e.get('start_time', '?')} \u2013 {e.get('end_time', '?')}"
        subject = e.get('subject', '')
        faculty = e.get('faculty', '') or 'TBD'
        room = e.get('room', '') or 'TBD'
        
        # Visual markers
        if e.get('is_break'):
            subject = f"\u2615 {subject}" if '\u2615' not in subject and '\U0001f37d' not in subject else subject
        elif e.get('is_lab'):
            subject = f"\u2697\ufe0f {subject}"
        elif 'CONFLICT' in subject:
            subject = f"\u26a0\ufe0f {subject}"
        
        lines.append(f"| {time_slot} | {subject} | {faculty} | {room} |")
    
    return "\n".join(lines) + "\n"


def format_week_timetable(entries: List[Dict[str, Any]]) -> str:
    """
    Format a full week's timetable as per-day tables with breaks.
    Each day gets its own header and table.
    """
    if not entries:
        return "No classes found for the week."
    
    # Group by day
    by_day: Dict[str, List[Dict[str, Any]]] = {}
    for e in entries:
        day = e.get('day', '')
        if day not in by_day:
            by_day[day] = []
        by_day[day].append(e)
    
    # Output each day in order
    parts = ["**\U0001f4c5 Weekly Timetable**\n"]
    for day in DAYS:
        day_entries = by_day.get(day, [])
        if day_entries:
            parts.append(format_day_table(day_entries, day))
            parts.append("")
    
    return "\n".join(parts)


def format_free_periods(entries: List[Dict[str, Any]], day: str = None) -> str:
    """Format free period results with actual times (never '?')."""
    if not entries:
        return "No free periods found."
    
    lines = [f"**Free Periods{f' for {day}' if day else ''}**\n", 
             "| Free From | Free Until | Duration |", 
             "|-----------|------------|----------|"]
    for e in entries:
        free_from = str(e.get('free_from', ''))
        free_until = str(e.get('free_until', ''))
        # Compute duration
        try:
            from datetime import datetime as dt
            t1 = dt.strptime(free_from, "%H:%M")
            t2 = dt.strptime(free_until, "%H:%M")
            diff = t2 - t1
            minutes = int(diff.total_seconds() / 60)
            duration = f"{minutes} min"
        except:
            duration = "-"
        lines.append(f"| {free_from} | {free_until} | {duration} |")
    
    return "\n".join(lines) + "\n"


def format_count_result(count: int) -> str:
    """Format a count query result."""
    return f"**Total classes: {count}**\n"


def format_single_class(entry: Dict[str, Any], label: str = "Next class") -> str:
    """Format a single class entry."""
    if not entry:
        return f"No {label.lower()} found."
    
    subject = entry.get('subject', 'Unknown')
    if entry.get('is_lab'):
        subject = f"\u2697\ufe0f {subject}"
    time_slot = f"{entry.get('start_time', '?')} \u2013 {entry.get('end_time', '?')}"
    day = entry.get('day', '')
    faculty = entry.get('faculty', '') or 'TBD'
    room = entry.get('room', '') or 'TBD'
    
    return f"**{label}:** {subject}\n\n| Field | Value |\n|-------|-------|\n| Day | {day} |\n| Time | {time_slot} |\n| Faculty | {faculty} |\n| Room | {room} |\n"


def format_conflicts(entries: List[Dict[str, Any]]) -> str:
    """Format timetable conflicts."""
    if not entries:
        return "\u2705 No timetable conflicts found!"
    
    lines = [f"**\u26a0\ufe0f Found {len(entries)} conflict(s):**\n", 
             "| Day | Conflict | Faculty | Room |", 
             "|-----|----------|---------|------|"]
    for e in entries:
        lines.append(f"| {e.get('day', '')} | {e.get('subject', '')} | {e.get('faculty', '')} | {e.get('room', '')} |")
    return "\n".join(lines) + "\n"


def filter_llm_reasoning(answer: str) -> str:
    """Remove structured LLM reasoning blocks, only display human-readable text."""
    answer = re.sub(r'{[^}]*type\s*:\s*reasoning[^}]*}', '', answer)
    return answer
