"""
Thread Store - Safe, persistent in-memory storage for conversation threads.

This module provides a SINGLE SOURCE OF TRUTH for thread storage with strict
separation between read and write operations to prevent accidental resets.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import logging
logger = logging.getLogger(__name__)


@dataclass
class Turn:
    """A single conversation turn."""
    role: str  # "user" | "assistant" | "system" | "tool"
    content: str


@dataclass
class Thread:
    """Thread with conversation turns."""
    thread_id: str
    turns: List[Turn] = field(default_factory=list)


# SINGLE, process-wide in-memory store
# This is the ONLY place where THREADS dict is defined
THREADS: Dict[str, Thread] = {}


def get_thread(thread_id: str) -> Optional[Thread]:
    """
    Pure lookup - NEVER creates or overwrites.
    
    This is the ONLY function that should be used in read paths (context builder).
    """
    thread_id = str(thread_id)
    thread = THREADS.get(thread_id)
    logger.info(f"[THREAD_STORE] get_thread: id={thread_id!r}, exists={thread is not None}, obj_id={id(thread) if thread else None}, turns={len(thread.turns) if thread else 0}")
    return thread


def get_or_create_thread(thread_id: str) -> Thread:
    """
    Safe create - only creates if missing, otherwise returns existing.
    
    This is the ONLY function that should be used in write paths (add_turn).
    """
    thread_id = str(thread_id)
    thread = THREADS.get(thread_id)
    if thread is not None:
        logger.info(f"[THREAD_STORE] get_or_create_thread: existing id={thread_id!r}, obj_id={id(thread)}, turns={len(thread.turns)}")
        return thread
    
    # Only create if missing
    thread = Thread(thread_id=thread_id)
    THREADS[thread_id] = thread
    logger.info(f"[THREAD_STORE] get_or_create_thread: NEW id={thread_id!r}, obj_id={id(thread)}")
    return thread


def add_turn(thread_id: str, turn: Turn) -> None:
    """
    Add a turn to a thread. Creates thread if it doesn't exist.
    
    This is the ONLY function that should be used to add turns.
    """
    thread = get_or_create_thread(thread_id)
    logger.info(f"[THREAD_STORE] add_turn BEFORE: id={thread_id!r}, obj_id={id(thread)}, len(turns)={len(thread.turns)}")
    thread.turns.append(turn)
    logger.info(f"[THREAD_STORE] add_turn AFTER: id={thread_id!r}, obj_id={id(thread)}, len(turns)={len(thread.turns)}")


def get_history(thread_id: str, max_turns: int = 12) -> List[Turn]:
    """
    Get conversation history for a thread. Returns empty list if thread doesn't exist.
    
    This is the ONLY function that should be used in read paths (context builder).
    """
    thread = get_thread(thread_id)
    if thread is None:
        logger.info(f"[THREAD_STORE] get_history: no thread for id={thread_id!r}")
        return []
    
    logger.info(f"[THREAD_STORE] get_history: id={thread_id!r}, obj_id={id(thread)}, len(turns)={len(thread.turns)}")
    if len(thread.turns) > max_turns:
        return list(thread.turns[-max_turns:])
    return list(thread.turns)


def clear_thread(thread_id: str) -> None:
    """
    Explicitly clear a thread's turns. Only use for explicit "reset conversation" actions.
    
    DO NOT call this in normal request handling paths.
    """
    thread = get_thread(thread_id)
    if thread is not None:
        logger.info(f"[THREAD_STORE] clear_thread: id={thread_id!r}, clearing {len(thread.turns)} turns")
        thread.turns.clear()
    else:
        logger.info(f"[THREAD_STORE] clear_thread: id={thread_id!r}, thread does not exist")

