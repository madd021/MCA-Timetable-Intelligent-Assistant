"""
LLM Client for the MCA Timetable Intelligent Assistant.
Supports two modes:
  1. OpenAI-compatible (databricks-sdk or openai package) for standalone apps
  2. Direct HTTP requests as fallback

FIXES ADDRESSED:
  - Missing 'openai' module: graceful fallback to requests-based HTTP calls
  - Never exposes credentials in logs or responses
"""
import json
import logging
import os
from typing import Dict, List, Any, Optional

from .config import config

logger = logging.getLogger(__name__)

_CLIENT_MODE = None
_openai_client = None


def init_llm_client():
    """Initialize the LLM client. Tries openai package, falls back to requests."""
    global _CLIENT_MODE, _openai_client
    
    # Try openai package first
    try:
        from openai import OpenAI
        _openai_client = OpenAI(
            base_url=f"{config.databricks_host.rstrip('/')}/serving-endpoints",
            api_key=config.databricks_token or "dummy",
        )
        _CLIENT_MODE = "openai"
        logger.info("LLM client initialized (openai mode)")
        return
    except ImportError:
        logger.info("openai package not available, falling back to requests")
    except Exception as e:
        logger.info(f"openai init failed ({e}), falling back to requests")
    
    # Try requests-based HTTP
    try:
        import requests
        _CLIENT_MODE = "requests"
        logger.info("LLM client initialized (requests mode)")
        return
    except ImportError:
        pass
    
    _CLIENT_MODE = None
    logger.warning("No LLM client available")


def call_llm(
    messages: List[Dict[str, str]],
    tools: List[Dict[str, Any]] = None,
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> Dict[str, Any]:
    """
    Call the LLM with messages and optional tool definitions.
    Returns dict with 'content' (str), 'tool_calls' (list), or 'error' (str).
    """
    global _openai_client
    
    if _CLIENT_MODE is None:
        init_llm_client()
    
    if _CLIENT_MODE == "openai" and _openai_client:
        try:
            kwargs = {
                "model": config.llm_endpoint,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if tools:
                kwargs["tools"] = tools
            response = _openai_client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            result = {"content": choice.message.content or "", "tool_calls": []}
            if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    result["tool_calls"].append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    })
            return result
        except Exception as e:
            logger.exception("OpenAI LLM call failed")
            return {"content": "", "tool_calls": [], "error": str(e)}
    
    if _CLIENT_MODE == "requests":
        try:
            import requests
            url = config.llm_url
            headers = {
                "Authorization": f"Bearer {config.databricks_token}",
                "Content-Type": "application/json",
            }
            payload = {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if tools:
                payload["tools"] = tools
            
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            
            # Parse response
            if "choices" in data:
                choice = data["choices"][0]
                content = choice.get("message", {}).get("content", "")
                tool_calls = []
                for tc in choice.get("message", {}).get("tool_calls", []):
                    tool_calls.append({
                        "id": tc.get("id", ""),
                        "name": tc.get("function", {}).get("name", ""),
                        "arguments": tc.get("function", {}).get("arguments", "{}"),
                    })
                return {"content": content, "tool_calls": tool_calls}
            return {"content": str(data), "tool_calls": []}
        except Exception as e:
            logger.exception("Requests LLM call failed")
            return {"content": "", "tool_calls": [], "error": str(e)}
    
    return {"content": "LLM not available. Please install openai or requests.", "tool_calls": [], "error": "no_client"}


def guardrail_check(question: str) -> tuple[bool, str]:
    """
    Check if a question is timetable-related.
    Returns (allowed, reason).
    """
    if not question or not question.strip():
        return False, "Please ask a question about your timetable."
    
    q = question.lower().strip()
    
    # Timetable-related keywords
    timetable_keywords = [
        "class", "schedule", "timetable", "subject", "faculty", "teacher", "room",
        "day", "time", "today", "tomorrow", "monday", "tuesday", "wednesday",
        "thursday", "friday", "saturday", "lab", "break", "lunch", "free",
        "next", "previous", "first", "last", "how many", "conflict", "overlap",
        "semester", "section", "morning", "afternoon", "evening", "week",
        "exam", "lecture", "practical", "tutorial", "period", "slot",
    ]
    
    # Non-timetable topics that should be blocked
    blocked = [
        "weather", "news", "recipe", "cook", "movie", "song", "game",
        "joke", "story", "poem", "write", "code", "debug", "python",
        "java", "html", "css", "database", "install", "download",
        "president", "capital", "country", "history", "science",
    ]
    
    # Check blocked first (but allow if also timetable-related)
    has_timetable = any(kw in q for kw in timetable_keywords)
    has_blocked = any(kw in q for kw in blocked)
    
    # Hard-block topics that are never timetable-related
    hard_blocked = [
        "weather", "news", "recipe", "cook", "movie", "song", "game",
        "joke", "story", "poem", "write a", "president", "capital", "country",
    ]
    if any(kw in q for kw in hard_blocked):
        return False, "I can only answer questions about the MCA timetable. Please ask about your class schedule."
    
    # Soft-block topics only if no timetable keyword is present
    soft_blocked = [
        "install", "download", "debug",
    ]
    if any(kw in q for kw in soft_blocked) and not has_timetable:
        return False, "I can only answer questions about the MCA timetable. Please ask about your class schedule."
    
    return True, ""


def get_tool_definitions() -> List[Dict[str, Any]]:
    """Return tool definitions for the LLM."""
    return [
        {
            "type": "function",
            "function": {
                "name": "query_timetable",
                "description": (
                    "Use this tool for timetable-related questions involving class schedules, "
                    "subjects, faculty, rooms, days, times, labs, breaks, free periods, conflicts, "
                    "today/tomorrow classes, next/previous class, week timetable. "
                    "This tool queries the actual MCA timetable database."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "The student's timetable question"},
                        "semester": {"type": "integer", "description": "Student's semester (1, 2, or 3)"},
                        "section": {"type": "string", "description": "Student's section (A, B, C, or D)"},
                        "track": {"type": "string", "description": "Optional: academic track (Cloud Computing, Data Science, Cyber Security & Data Science)"},
                    },
                    "required": ["question", "semester", "section"],
                },
            },
        }
    ]
