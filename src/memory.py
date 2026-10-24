"""
Short-term conversation memory for follow-up questions.
Tracks: last subject, day, results, semester, section.
"""
from typing import Dict, List, Any, Optional


class ConversationMemory:
    """Short-term memory for timetable conversation context."""
    
    def __init__(self, max_history: int = 10):
        self.history: List[Dict[str, Any]] = []
        self.max_history = max_history
        self.last_subject: Optional[str] = None
        self.last_day: Optional[str] = None
        self.last_results: List[Dict[str, Any]] = []
        self.semester: Optional[int] = None
        self.section: Optional[str] = None
        self.track: Optional[str] = None
    
    def add(self, question: str, answer: str, results: List[Dict[str, Any]] = None):
        """Add a conversation exchange to memory."""
        self.history.append({"question": question, "answer": answer})
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
        if results:
            self.last_results = results
            for r in results:
                if isinstance(r, dict) and r.get('subject') and r['subject'] != 'FREE':
                    self.last_subject = r['subject']
                if isinstance(r, dict) and r.get('day'):
                    self.last_day = r['day']
    
    def resolve_followup(self, question: str) -> str:
        """Resolve follow-up references using memory context."""
        q_lower = question.lower().strip()
        
        # Pronoun resolution: "where is it?" -> "where is <last_subject>?"
        if self.last_subject:
            if q_lower in ["where?", "where is it?", "where is it", "what room?"]:
                return f"Where is {self.last_subject}?"
            if q_lower in ["who teaches it?", "who teaches it", "who?", "faculty?"]:
                return f"Who teaches {self.last_subject}?"
            if q_lower in ["when is it?", "when is it", "what time?"]:
                return f"When is {self.last_subject}?"
            if q_lower in ["which day?", "what day?"]:
                return f"Which day is {self.last_subject}?"
        
        # Day reference: "what about tomorrow?"
        if "tomorrow" in q_lower and self.last_subject:
            return f"What is the schedule for {self.last_subject} tomorrow?"
        
        return question
    
    def get_context(self) -> str:
        """Get memory context string for the LLM."""
        parts = []
        if self.semester:
            parts.append(f"Student semester: {self.semester}")
        if self.section:
            parts.append(f"Student section: {self.section}")
        if self.track:
            parts.append(f"Student track: {self.track}")
        if self.last_subject:
            parts.append(f"Last discussed subject: {self.last_subject}")
        if self.last_day:
            parts.append(f"Last discussed day: {self.last_day}")
        return "\n".join(parts) if parts else "No prior context"
    
    def reset(self):
        """Reset all memory."""
        self.history = []
        self.last_subject = None
        self.last_day = None
        self.last_results = []
