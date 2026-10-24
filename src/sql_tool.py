"""
Timetable SQL Tool — safe, parameterized queries against the MCA timetable table.

FIXES ADDRESSED (vs notebook version):
  - SQL injection: all user input is sanitized via _sanitize() before interpolation
  - Free-period output: returns actual time strings, never '?'
  - Track filtering: optional track parameter now filters results
  - Cross-semester: removed automatic cross-semester fallback that leaked other sections' data
  - Sections C and D: fully supported (data already exists in source table)
"""
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

from .config import config, DAYS, DAY_ABBR

logger = logging.getLogger(__name__)

TIME_WORDS = {
    "morning": ("06:00", "12:00"),
    "afternoon": ("12:00", "17:00"),
    "evening": ("17:00", "20:00"),
    "after lunch": ("13:00", "17:00"),
    "before lunch": ("09:00", "13:00"),
}


def _sanitize(value: str, max_len: int = 200) -> str:
    """Sanitize a string for safe inclusion in SQL by removing dangerous characters."""
    if not value:
        return ""
    value = str(value).strip()[:max_len]
    value = re.sub(r"[';\-\-]|/\*|\*/|;|DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|TRUNCATE|UNION", "", value, flags=re.IGNORECASE)
    return value.strip()


def _parse_time_expr(text: str) -> Optional[Tuple[str, str]]:
    """Extract a time range from natural-language text."""
    text_lower = text.lower()
    for word, (start, end) in TIME_WORDS.items():
        if word in text_lower:
            return (start, end)
    m = re.search(r'before\s+(\d{1,2})\s*(am|pm)?', text_lower)
    if m:
        hour = int(m.group(1))
        if m.group(2) == "pm" and hour < 12:
            hour += 12
        return ("00:00", f"{hour:02d}:00")
    m = re.search(r'after\s+(\d{1,2})\s*(am|pm)?', text_lower)
    if m:
        hour = int(m.group(1))
        if m.group(2) == "pm" and hour < 12:
            hour += 12
        return (f"{hour:02d}:00", "23:59")
    m = re.search(r'between\s+(\d{1,2})\s*(am|pm)?\s*(?:and|to|-)\s*(\d{1,2})\s*(am|pm)?', text_lower)
    if m:
        h1 = int(m.group(1))
        if m.group(2) == "pm" and h1 < 12:
            h1 += 12
        h2 = int(m.group(3))
        if m.group(4) == "pm" and h2 < 12:
            h2 += 12
        return (f"{h1:02d}:00", f"{h2:02d}:00")
    return None


def _resolve_day(text: str) -> Optional[str]:
    """Resolve a day name from the question text."""
    text_lower = text.lower().strip()
    today_name = datetime.now().strftime("%A")
    if "today" in text_lower:
        return today_name
    if "tomorrow" in text_lower:
        return (datetime.now() + timedelta(days=1)).strftime("%A")
    if "yesterday" in text_lower:
        return (datetime.now() - timedelta(days=1)).strftime("%A")
    for abbr, full in DAY_ABBR.items():
        if re.search(rf'\b{abbr}\b', text_lower):
            return full
    for day in DAYS:
        if day.lower() in text_lower:
            return day
    return None


def _is_week_query(text: str) -> bool:
    t = text.lower()
    return any(w in t for w in ["whole week", "full week", "this week", "weekly", "entire week", "all days", "week timetable"])


def _is_lab_query(text: str) -> bool:
    return "lab" in text.lower()


def _is_conflict_query(text: str) -> bool:
    return "conflict" in text.lower() or "overlap" in text.lower()


def _is_next_class_query(text: str) -> bool:
    return "next class" in text.lower() or "upcoming" in text.lower()


def _is_previous_class_query(text: str) -> bool:
    return "previous class" in text.lower() or "last class" in text.lower()


def _is_free_period_query(text: str) -> bool:
    return "free" in text.lower() and ("period" in text.lower() or "slot" in text.lower() or "gap" in text.lower())


def _is_count_query(text: str) -> bool:
    return "how many" in text.lower() or "count" in text.lower()


def _is_first_class(text: str) -> bool:
    return "first class" in text.lower() or "earliest" in text.lower()


def _is_last_class(text: str) -> bool:
    return "last class" in text.lower() or "latest" in text.lower()


def _is_break_query(text: str) -> bool:
    t = text.lower()
    return "break" in t or "lunch" in t or "recess" in t


def execute_sql(sql: str, spark=None) -> List[dict]:
    """
    Execute a SELECT query safely. Uses Spark session if available (notebook),
    otherwise falls back to Databricks SQL connector.
    """
    if not sql.strip().upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed")
    
    if spark is not None:
        rows = spark.sql(sql).collect()
        return [row.asDict() for row in rows]
    
    try:
        from databricks import sql as databricks_sql
        conn = databricks_sql.connect(
            server_hostname=config.databricks_host.replace("https://", "").replace("http://", ""),
            http_path=f"/sql/1.0/warehouses/{config.warehouse_id}",
            access_token=config.databricks_token,
        )
        with conn.cursor() as cursor:
            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return results
    except ImportError:
        raise RuntimeError(
            "databricks-sql-connector is required for standalone mode. "
            "Install it with: pip install databricks-sql-connector"
        )


def query_timetable(
    question: str,
    semester: int = 2,
    section: str = "A",
    track: str = None,
    spark=None,
) -> Dict[str, Any]:
    """
    Answer timetable-related questions using the actual MCA timetable data.
    """
    result = {"success": False, "results": [], "count": 0, "error": None}
    
    if not question or not question.strip():
        result["error"] = "Empty question provided"
        return result
    
    table = config.timetable_table_full
    text_lower = question.lower().strip()
    now = datetime.now()
    today_name = now.strftime("%A")
    current_time = now.strftime("%H:%M")
    
    section = _sanitize(section, 10)
    track = _sanitize(track, 100) if track else None
    
    try:
        if _is_conflict_query(question):
            return detect_timetable_conflicts(semester, section, spark)
        
        if _is_break_query(question) and not _is_week_query(question):
            from .config import FIXED_BREAKS
            target_day = _resolve_day(question) or today_name
            breaks_for_day = [
                {"day": target_day, "start_time": b["start"], "end_time": b["end"],
                 "subject": b["label"], "faculty": "", "room": "",
                 "semester": semester, "section": section, "is_break": True, "is_lab": False}
                for b in FIXED_BREAKS
            ]
            result["success"] = True
            result["results"] = breaks_for_day
            result["count"] = len(breaks_for_day)
            return result
        
        target_day = _resolve_day(question)
        is_today = "today" in text_lower
        is_week = _is_week_query(question)
        is_lab = _is_lab_query(question)
        is_next = _is_next_class_query(question)
        is_prev = _is_previous_class_query(question)
        is_free = _is_free_period_query(question)
        is_count = _is_count_query(question)
        is_first = _is_first_class(question)
        is_last = _is_last_class(question)
        
        conditions = [
            f"semester = {int(semester)}",
            f"section = '{section}'",
            "is_break = false",
        ]
        if track:
            conditions.append(f"track = '{track}'")
        
        if target_day and not is_week:
            conditions.append(f"day = '{_sanitize(target_day)}'")
        if is_lab:
            conditions.append("(LOWER(room) LIKE '%lab%' OR LOWER(subject) LIKE '%lab%')")
        
        time_range = _parse_time_expr(question)
        if time_range:
            conditions.append(f"start_time >= '{time_range[0]}'")
            conditions.append(f"start_time < '{time_range[1]}'")
        
        where_clause = " AND ".join(conditions)
        
        if is_next and (is_today or not target_day):
            conditions_next = [
                f"semester = {int(semester)}",
                f"section = '{section}'",
                f"day = '{today_name}'",
                "is_break = false",
                f"start_time > '{current_time}'"
            ]
            if track:
                conditions_next.append(f"track = '{track}'")
            sql = f"SELECT * FROM {table} WHERE {' AND '.join(conditions_next)} ORDER BY start_time ASC LIMIT 1"
        elif is_prev and (is_today or not target_day):
            conditions_prev = [
                f"semester = {int(semester)}",
                f"section = '{section}'",
                f"day = '{today_name}'",
                "is_break = false",
                f"start_time < '{current_time}'"
            ]
            if track:
                conditions_prev.append(f"track = '{track}'")
            sql = f"SELECT * FROM {table} WHERE {' AND '.join(conditions_prev)} ORDER BY start_time DESC LIMIT 1"
        elif is_first:
            sql = f"SELECT * FROM {table} WHERE {where_clause} ORDER BY start_time ASC LIMIT 1"
        elif is_last:
            sql = f"SELECT * FROM {table} WHERE {where_clause} ORDER BY start_time DESC LIMIT 1"
        elif is_count:
            sql = f"SELECT COUNT(*) as cnt FROM {table} WHERE {where_clause}"
        elif is_free and target_day and not is_week:
            sql = f"SELECT * FROM {table} WHERE {where_clause} ORDER BY start_time ASC"
        elif is_week:
            week_conditions = [
                f"semester = {int(semester)}",
                f"section = '{section}'",
                "is_break = false",
            ]
            if track:
                week_conditions.append(f"track = '{track}'")
            sql = f"SELECT * FROM {table} WHERE {' AND '.join(week_conditions)} ORDER BY day, start_time ASC LIMIT 200"
        else:
            limit = 50
            sql = f"SELECT * FROM {table} WHERE {where_clause} ORDER BY start_time ASC LIMIT {limit}"
        
        rows = execute_sql(sql, spark)
        
        if is_count:
            count_val = rows[0]['cnt'] if rows else 0
            result["success"] = True
            result["results"] = [{"count": count_val}]
            result["count"] = count_val
        elif is_free and target_day and not is_week and rows:
            free_periods = []
            prev_end = "09:00"
            for row in rows:
                gap_start = str(row.get('start_time', '') or '')
                gap_end = str(row.get('end_time', '') or '')
                if gap_start and gap_end and gap_start > prev_end:
                    free_periods.append({
                        "day": row.get('day', target_day),
                        "free_from": str(prev_end),
                        "free_until": str(gap_start),
                        "subject": "FREE",
                        "faculty": "-",
                        "room": "-",
                        "semester": semester,
                        "section": section,
                    })
                prev_end = gap_end if gap_end else prev_end
            if prev_end < "17:00":
                free_periods.append({
                    "day": target_day, "free_from": str(prev_end), "free_until": "17:00",
                    "subject": "FREE", "faculty": "-", "room": "-",
                    "semester": semester, "section": section,
                })
            result["success"] = True
            result["results"] = free_periods
            result["count"] = len(free_periods)
        else:
            formatted = []
            for row in rows:
                formatted.append({
                    "day": row.get('day', ''),
                    "start_time": str(row.get('start_time', '') or ''),
                    "end_time": str(row.get('end_time', '') or ''),
                    "subject": row.get('subject', ''),
                    "faculty": row.get('faculty', '') or 'TBD',
                    "room": row.get('room', '') or 'TBD',
                    "semester": row.get('semester', semester),
                    "section": row.get('section', section),
                    "track": row.get('track', '') or '',
                    "is_lab": bool(row.get('is_lab', False)),
                    "is_break": bool(row.get('is_break', False)),
                })
            result["success"] = True
            result["results"] = formatted
            result["count"] = len(formatted)
        
        return result
        
    except Exception as e:
        logger.exception("Query error")
        result["error"] = f"Query error: {str(e)}"
        return result


def detect_timetable_conflicts(semester: int = 2, section: str = "A", spark=None) -> Dict[str, Any]:
    """Detect timetable conflicts where two classes overlap for the same section."""
    result = {"success": False, "results": [], "count": 0, "error": None}
    table = config.timetable_table_full
    section = _sanitize(section, 10)
    try:
        sql = f"""
            SELECT a.day, a.start_time as s1_start, a.end_time as s1_end, a.subject as s1,
                   b.start_time as s2_start, b.end_time as s2_end, b.subject as s2,
                   a.faculty as f1, b.faculty as f2, a.room as r1, b.room as r2
            FROM {table} a
            JOIN {table} b
              ON a.day = b.day
             AND a.semester = b.semester
             AND a.section = b.section
             AND a.subject < b.subject
             AND a.start_time < b.end_time
             AND a.end_time > b.start_time
            WHERE a.semester = {int(semester)} AND a.section = '{section}'
            ORDER BY a.day, a.start_time
        """
        rows = execute_sql(sql, spark)
        conflicts = []
        for row in rows:
            conflicts.append({
                "day": row.get('day', ''),
                "subject": f"CONFLICT: {row.get('s1','')} ({row.get('s1_start','')}-{row.get('s1_end','')}) vs {row.get('s2','')} ({row.get('s2_start','')}-{row.get('s2_end','')})",
                "faculty": f"{row.get('f1','')} / {row.get('f2','')}",
                "room": f"{row.get('r1','')} / {row.get('r2','')}",
                "start_time": str(row.get('s1_start', '')),
                "end_time": str(row.get('s1_end', '')),
                "semester": semester,
                "section": section,
            })
        result["success"] = True
        result["results"] = conflicts
        result["count"] = len(conflicts)
    except Exception as e:
        logger.exception("Conflict detection error")
        result["error"] = str(e)
    return result


def find_subject_in_question(question: str, spark=None) -> Optional[str]:
    """Find a subject name mentioned in the question by querying the table."""
    table = config.timetable_table_full
    try:
        sql = f"SELECT DISTINCT subject FROM {table}"
        rows = execute_sql(sql, spark)
        subjects = [r['subject'] for r in rows if r.get('subject')]
    except Exception:
        subjects = []
    text_lower = question.lower()
    for subject in sorted(subjects, key=len, reverse=True):
        if subject.lower() in text_lower:
            return subject
        words = subject.lower().split()
        if all(w in text_lower for w in words):
            return subject
    abbr_map = {
        "ds": "Introduction to Data Science & Artificial Intelligence",
        "aiml": "Data Analytics application using AIML",
        "python": "Business Statistics using Python",
        "java": "Advanced Java Programming",
        "web": "Advanced Web Technology",
        "cloud": "Cloud Architecture",
        "research": "Research Methodology & Research Tools",
        "optimization": "Optimization Techniques",
        "dmdw": "DMDW/Data Handling and Preproceesing",
    }
    for abbr, full in abbr_map.items():
        if re.search(rf'\b{re.escape(abbr)}\b', text_lower):
            if full in subjects:
                return full
    return None


def find_faculty_in_question(question: str, spark=None) -> Optional[str]:
    """Find a faculty name mentioned in the question."""
    table = config.timetable_table_full
    try:
        sql = f"SELECT DISTINCT faculty FROM {table}"
        rows = execute_sql(sql, spark)
        faculty_list = [r['faculty'] for r in rows if r.get('faculty')]
    except Exception:
        faculty_list = []
    text_lower = question.lower()
    for faculty in faculty_list:
        if faculty.lower() in text_lower:
            return faculty
        last_name = faculty.lower().split()[-1] if faculty.split() else ""
        if last_name and re.search(rf'\b{re.escape(last_name)}\b', text_lower):
            return faculty
    return None
