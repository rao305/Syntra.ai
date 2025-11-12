"""Memory Manager for Conversation Context Preservation.

Maintains rolling conversation history with summarization fallback
to ensure context is preserved across all turns.
"""
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, field

# Dynamic window management
DEFAULT_THREAD_WINDOW = 12  # Default: Keep last 12 turns verbatim
MIN_THREAD_WINDOW = 6  # Minimum window size
MAX_THREAD_WINDOW = 50  # Maximum window size

def get_dynamic_window(model_context_limit: Optional[int] = None, task_complexity: str = "normal") -> int:
    """
    Calculate dynamic memory window based on model context limits and task complexity.
    
    Args:
        model_context_limit: Maximum context tokens for the model (e.g., 8192, 32768, 128000)
        task_complexity: "simple", "normal", "complex"
    
    Returns:
        Optimal window size (number of turns to keep verbatim)
    """
    base_window = DEFAULT_THREAD_WINDOW
    
    # Adjust based on task complexity
    complexity_multipliers = {
        "simple": 0.7,
        "normal": 1.0,
        "complex": 1.5
    }
    multiplier = complexity_multipliers.get(task_complexity, 1.0)
    adjusted_window = int(base_window * multiplier)
    
    # Adjust based on model context limit if provided
    if model_context_limit:
        # Estimate: ~100 tokens per turn on average
        estimated_tokens_per_turn = 100
        max_turns_by_context = (model_context_limit * 0.7) // estimated_tokens_per_turn  # Use 70% for conversation
        adjusted_window = min(adjusted_window, max_turns_by_context)
    
    # Clamp to min/max bounds
    return max(MIN_THREAD_WINDOW, min(MAX_THREAD_WINDOW, adjusted_window))


@dataclass
class Turn:
    """A single conversation turn."""
    role: str  # "user", "assistant", or "system"
    content: str
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class Thread:
    """Thread with rolling memory."""
    id: str
    summary: Optional[str] = None  # Rolling abstract of earlier turns
    turns: List[Turn] = field(default_factory=list)
    name: Optional[str] = None  # e.g., "Alex"
    project: Optional[str] = None  # e.g., "Python project"
    last_intent: Optional[str] = None  # For intent smoothing


# In-memory store (swap for Redis in production)
_thread_store: Dict[str, Thread] = {}


def get_thread(thread_id: str) -> Thread:
    """Get or create a thread."""
    if thread_id not in _thread_store:
        _thread_store[thread_id] = Thread(id=thread_id)
    return _thread_store[thread_id]


def initialize_thread_from_db(thread_id: str, db_messages: List[Dict[str, str]]) -> None:
    """
    Initialize thread memory from database messages.
    
    Call this when loading an existing thread to populate memory manager
    with prior conversation history.
    
    Args:
        thread_id: Thread ID
        db_messages: List of messages from database in format [{"role": "user|assistant", "content": "..."}, ...]
    """
    thread = get_thread(thread_id)
    
    # Only initialize if thread is empty (first access)
    if not thread.turns and db_messages:
        for msg in db_messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ["user", "assistant"] and content:
                turn = Turn(role=role, content=content)
                thread.turns.append(turn)
                
                # Extract profile facts from user messages
                if role == "user":
                    extract_profile_facts(thread, content)
        
        # Apply windowing if we have more than THREAD_WINDOW messages
        if len(thread.turns) > THREAD_WINDOW:
            older_turns = thread.turns[:-THREAD_WINDOW]
            thread.turns = thread.turns[-THREAD_WINDOW:]
            
            if older_turns:
                older_text = "\n".join([f"{t.role}: {t.content}" for t in older_turns])
                thread.summary = summarize_rolling(thread.summary, older_text)


def add_turn(thread_id: str, turn: Turn, model_context_limit: Optional[int] = None, task_complexity: str = "normal") -> None:
    """
    Add a turn to the thread and manage windowing with dynamic adjustment.
    
    Args:
        thread_id: Thread identifier
        turn: Turn to add
        model_context_limit: Optional model context limit for dynamic window sizing
        task_complexity: "simple", "normal", or "complex" for window adjustment
    """
    thread = get_thread(thread_id)
    thread.turns.append(turn)
    
    # Extract profile facts from user messages
    if turn.role == "user":
        extract_profile_facts(thread, turn.content)
    
    # Calculate dynamic window size
    dynamic_window = get_dynamic_window(model_context_limit, task_complexity)
    
    # Window management: if we exceed dynamic window, summarize older turns
    if len(thread.turns) > dynamic_window:
        # Get turns to summarize (everything except the last dynamic_window)
        older_turns = thread.turns[:-dynamic_window]
        thread.turns = thread.turns[-dynamic_window:]
        
        # Summarize older turns
        if older_turns:
            older_text = "\n".join([f"{t.role}: {t.content}" for t in older_turns])
            thread.summary = summarize_rolling(thread.summary, older_text)


def extract_profile_facts(thread: Thread, user_text: str) -> None:
    """Extract obvious facts like name and project from user messages."""
    import re
    
    # Extract name: "I'm Alex", "My name is Alex", "call me Alex"
    name_patterns = [
        r"i'?m\s+([A-Z][a-z]+)",
        r"my name is\s+([A-Z][a-z]+)",
        r"call me\s+([A-Z][a-z]+)",
        r"i'?m\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
    ]
    for pattern in name_patterns:
        match = re.search(pattern, user_text, re.IGNORECASE)
        if match:
            thread.name = match.group(1).strip()
            break
    
    # Extract project: "Python project", "working on Python", "building a Python app"
    project_patterns = [
        r"(?:working on|building|project).*?(python|javascript|react|django|flask|node)",
        r"(python|javascript|react|django|flask|node)\s+project",
    ]
    for pattern in project_patterns:
        match = re.search(pattern, user_text, re.IGNORECASE)
        if match:
            project_type = match.group(1).lower()
            thread.project = f"{project_type.capitalize()} project"
            break


def summarize_rolling(prev_summary: Optional[str], new_chunk: str) -> str:
    """
    Summarize rolling conversation history.
    
    Simple concatenation fallback - in production, replace with LLM call for quality.
    """
    cap = 2000  # characters
    merged = ((prev_summary or "") + "\n" + new_chunk).strip()
    if len(merged) > cap:
        # Truncate from the beginning, keeping the most recent
        merged = "..." + merged[-cap:]
    return merged


def build_prompt_for_model(thread_id: str, persona: str) -> List[Dict[str, str]]:
    """
    Build the complete prompt array for model calls.
    
    Structure:
    1. System persona
    2. Conversation summary (if exists)
    3. Known user facts (name, project)
    4. Recent turns (last THREAD_WINDOW)
    """
    thread = get_thread(thread_id)
    messages: List[Dict[str, str]] = []
    
    # 1. System persona
    messages.append({
        "role": "system",
        "content": persona
    })
    
    # 2. Conversation summary
    if thread.summary:
        messages.append({
            "role": "system",
            "content": f"Conversation summary (source of truth): {thread.summary}"
        })
    
    # 3. Known user facts
    if thread.name or thread.project:
        facts = []
        if thread.name:
            facts.append(f"name={thread.name}")
        if thread.project:
            facts.append(f"project={thread.project}")
        messages.append({
            "role": "system",
            "content": f"Known user facts: {', '.join(facts)}"
        })
    
    # 4. Recent turns
    for turn in thread.turns:
        messages.append({
            "role": turn.role,
            "content": turn.content
        })
    
    return messages


def smooth_intent(current_intent: str, thread_id: str, user_text: str) -> str:
    """
    Smooth intent detection using context from previous turn.
    
    If previous turn was coding_help and current is ambiguous but looks like explanation,
    force qa_retrieval.
    """
    thread = get_thread(thread_id)
    
    # Check if this looks like a follow-up explanation
    is_followup_explain = bool(re.search(
        r"\b(explain|why|how does|what does this do|what's the|tell me about)\b",
        user_text,
        re.IGNORECASE
    ))
    
    # If previous intent was coding_help and current is ambiguous/social but looks like explanation
    if (thread.last_intent == "coding_help" and 
        current_intent in ["ambiguous_or_other", "social_chat"] and 
        is_followup_explain):
        return "qa_retrieval"
    
    return current_intent


def update_last_intent(thread_id: str, intent: str) -> None:
    """Update the last detected intent for a thread."""
    thread = get_thread(thread_id)
    thread.last_intent = intent


# Import re at module level
import re

