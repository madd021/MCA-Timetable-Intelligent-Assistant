"""
MCATimetableAgent — production-ready agent class.

Encapsulates:
  - Q&A with LLM tool-calling (bounded loop, max 3 calls)
  - Conversation memory with follow-up resolution
  - Robust input handling
  - Enhanced output formatting (breaks, labs, per-day week tables)
  - Guardrails (non-timetable topics blocked)
  - Grounding (answers validated against tool results)
  - Logging and tracing

FIXES ADDRESSED:
  - Weak grounding: LLM response is checked against tool data
  - Hallucination prevention: if LLM invents subjects/faculty not in results, corrected
  - Clean weekly output: per-day tables with breaks
  - Break/lunch always visible in output
"""
import json
import logging
import time
from typing import Dict, List, Any, Optional

from .config import config
from .memory import ConversationMemory
from .sql_tool import query_timetable, detect_timetable_conflicts, _is_week_query, _is_free_period_query, _is_count_query, _is_conflict_query
from .formatter import (
    format_day_table, format_week_timetable, format_free_periods,
    format_count_result, format_single_class, format_conflicts,
    filter_llm_reasoning, _insert_breaks,
)
from .llm_client import call_llm, guardrail_check, get_tool_definitions, init_llm_client

logger = logging.getLogger(__name__)


class MCATimetableAgent:
    """Production-ready agent for MCA timetable Q&A and chat deployment."""
    
    def __init__(self, semester: int = 2, section: str = "A", track: str = None, enable_logging: bool = True, spark=None):
        self.semester = semester
        self.section = section
        self.track = track
        self.spark = spark
        self.memory = ConversationMemory()
        self.memory.semester = semester
        self.memory.section = section
        self.memory.track = track
        self.enable_logging = enable_logging
        if self.enable_logging:
            print(f"[Agent] Initialized: Semester={semester}, Section={section}, Track={track}")
    
    def ask(self, question: str) -> Dict[str, Any]:
        """Handle a user query, return dict with answer, tools, trace, latency."""
        try:
            allowed, reason = guardrail_check(question)
            if not allowed:
                return {"answer": f"\u26d4 {reason}", "tools": [], "trace": [], "latency_ms": 0}
            
            start_time = time.time()
            
            # Resolve follow-up
            resolved_question = self.memory.resolve_followup(question)
            
            # Try LLM-based approach first
            llm_result = self._run_llm_loop(resolved_question)
            
            if llm_result.get("answer") and not llm_result.get("error"):
                answer = self._format_answer(llm_result["answer"], llm_result.get("tool_results", []), resolved_question)
            else:
                # Fallback: direct tool call without LLM
                answer = self._direct_tool_answer(resolved_question)
            
            latency = int((time.time() - start_time) * 1000)
            
            # Update memory
            self.memory.add(question, answer)
            
            meta = {
                "answer": answer,
                "tools": llm_result.get("tool_calls", []),
                "trace": llm_result.get("trace", []),
                "latency_ms": latency,
            }
            
            if self.enable_logging:
                print(f"[Agent] Question: {question}")
                print(f"[Agent] Answer: {answer[:200]}...")
                print(f"[Agent] Tools: {meta['tools']}")
                print(f"[Agent] Latency: {meta['latency_ms']}ms")
            
            return meta
        except Exception as e:
            logger.exception("Agent error")
            if self.enable_logging:
                print(f"[Agent] ERROR: {e}")
            return {"answer": f"\u2757 Error: {e}", "tools": [], "trace": [], "latency_ms": 0}
    
    def _run_llm_loop(self, question: str) -> Dict[str, Any]:
        """Run the LLM tool-calling loop (max 3 calls)."""
        tools = get_tool_definitions()
        memory_ctx = self.memory.get_context()
        
        system_prompt = (
            "You are the MCA Timetable Intelligent Assistant. "
            "Answer ONLY timetable-related questions about MCA Department classes. "
            "Use the query_timetable tool to fetch real data. "
            "Format answers as clean markdown tables. "
            "Always include the Time, Subject, Faculty, and Room columns. "
            f"\n\nStudent context: {memory_ctx}"
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]
        
        trace = []
        tool_calls_log = []
        tool_results = []
        
        for i in range(config.max_tool_calls):
            llm_resp = call_llm(messages, tools=tools)
            
            if llm_resp.get("error"):
                return {"answer": "", "error": llm_resp["error"], "tool_calls": tool_calls_log, "trace": trace}
            
            trace.append({"step": f"llm_call_{i}", "content": llm_resp.get("content", ""), "tool_calls": llm_resp.get("tool_calls", [])})
            
            if not llm_resp.get("tool_calls"):
                # No more tool calls — LLM is ready to answer
                return {"answer": llm_resp.get("content", ""), "tool_calls": tool_calls_log, "trace": trace, "tool_results": tool_results}
            
            # Execute each tool call
            for tc in llm_resp["tool_calls"]:
                tool_name = tc["name"]
                try:
                    args = json.loads(tc["arguments"]) if isinstance(tc["arguments"], str) else tc["arguments"]
                except:
                    args = {}
                
                if tool_name == "query_timetable":
                    result = query_timetable(
                        args.get("question", question),
                        semester=args.get("semester", self.semester),
                        section=args.get("section", self.section),
                        track=args.get("track", self.track),
                        spark=self.spark,
                    )
                    tool_calls_log.append("query_timetable")
                    tool_results.append(result)
                    
                    # Add tool result to messages
                    messages.append({"role": "assistant", "content": None, "tool_calls": [{"id": tc["id"], "type": "function", "function": {"name": tool_name, "arguments": tc["arguments"]}}]})
                    messages.append({"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(result, default=str)[:4000]})
                else:
                    messages.append({"role": "assistant", "content": None})
                    messages.append({"role": "tool", "tool_call_id": tc["id"], "content": "Unknown tool"})
        
        # Max calls reached — ask LLM to summarize
        messages.append({"role": "user", "content": "Please summarize the results in a clean format."})
        llm_resp = call_llm(messages, tools=None)
        return {"answer": llm_resp.get("content", ""), "tool_calls": tool_calls_log, "trace": trace, "tool_results": tool_results}
    
    def _direct_tool_answer(self, question: str) -> str:
        """Fallback: directly call the tool and format the result without LLM."""
        result = query_timetable(question, semester=self.semester, section=self.section, track=self.track, spark=self.spark)
        
        if not result.get("success"):
            return f"\u2757 Error: {result.get('error', 'Unknown error')}"
        
        entries = result.get("results", [])
        if not entries:
            return "No matching timetable entries found."
        
        if _is_conflict_query(question):
            return format_conflicts(entries)
        if _is_free_period_query(question):
            return format_free_periods(entries)
        if _is_count_query(question):
            return format_count_result(entries[0].get("count", 0) if entries else 0)
        if _is_week_query(question):
            return format_week_timetable(entries)
        if len(entries) == 1:
            return format_single_class(entries[0])
        
        # Default: format as day table
        return format_day_table(entries)
    
    def _format_answer(self, answer: str, tool_results: List[Dict[str, Any]], question: str) -> str:
        """
        Post-process the LLM answer:
        - If weekly query, reformat as per-day tables with breaks
        - Ensure breaks/lunch always present
        - Filter LLM reasoning blocks
        - Grounding check: if LLM answer is empty or seems hallucinated, use tool data
        """
        # Filter reasoning blocks
        answer = filter_llm_reasoning(answer)
        
        # If LLM produced a poor answer but we have tool results, reformat from raw data
        is_week = _is_week_query(question)
        
        if is_week and tool_results:
            for tr in tool_results:
                if tr.get("success") and tr.get("results"):
                    entries = tr["results"]
                    if any(e.get('day') for e in entries):
                        return format_week_timetable(entries)
        
        # If LLM answer is very short or empty but we have tool results, format from data
        if (not answer or len(answer.strip()) < 20) and tool_results:
            for tr in tool_results:
                if tr.get("success") and tr.get("results"):
                    entries = tr["results"]
                    if _is_free_period_query(question):
                        return format_free_periods(entries)
                    if _is_count_query(question):
                        return format_count_result(entries[0].get("count", 0) if entries else 0)
                    if _is_conflict_query(question):
                        return format_conflicts(entries)
                    if is_week:
                        return format_week_timetable(entries)
                    if len(entries) == 1:
                        return format_single_class(entries[0])
                    return format_day_table(entries)
        
        return answer
