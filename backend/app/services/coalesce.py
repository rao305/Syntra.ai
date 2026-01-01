import asyncio
import time
import hashlib
import json
from typing import Any, Awaitable, Callable, Dict, Optional


class _Entry:
    __slots__ = ("evt", "result", "error", "done", "ts")
    
    def __init__(self):
        self.evt = asyncio.Event()
        self.result = None
        self.error = None
        self.done = False
        self.ts = time.monotonic()


class Coalescer:
    def __init__(self, ttl_sec: float = 30.0):
        self._inflight: Dict[str, _Entry] = {}
        self._lock = asyncio.Lock()
        self.ttl = ttl_sec
    
    def _gc(self):
        now = time.monotonic()
        for k, v in list(self._inflight.items()):
            if v.done and (now - v.ts) > self.ttl:
                self._inflight.pop(k, None)
    
    async def run(self, key: str, leader_fn: Callable[[], Awaitable[dict]]):
        """Returns dict result. Only leader executes leader_fn; followers wait & reuse."""
        self._gc()
        
        async with self._lock:
            ent = self._inflight.get(key)
            if ent is None:
                ent = _Entry()
                self._inflight[key] = ent
                leader = True
            else:
                leader = False
        
        if not leader:
            # Track follower event
            try:
                from app.services.performance import performance_monitor
                performance_monitor.log_event("coalesce_follower")
            except Exception:
                pass  # Don't fail if performance module not available
            
            await ent.evt.wait()
            if ent.error:
                raise ent.error
            return ent.result

    
        
        try:
            # Track leader event
            try:
                from app.services.performance import performance_monitor
                performance_monitor.log_event("coalesce_leader")
            except Exception:
                pass  # Don't fail if performance module not available
            
            result = await leader_fn()
            ent.result = result
            return result
        except Exception as e:
            ent.error = e
            # Shorten lifetime for errors (2s) so callers retry soon
            ent.ts = time.monotonic() - (self.ttl - 2)  # expires quickly
            raise
        finally:
            ent.done = True
            ent.evt.set()
            self._gc()


coalescer = Coalescer(ttl_sec=30.0)


def coalesce_key(provider: str, model: str, messages: list, thread_id: Optional[str] = None) -> str:
    """Generate coalesce key.
    
    For identical concurrent requests, use thread_id + new message content.
    This ensures requests coalesce even if conversation state changes between waves.
    """
    if thread_id and messages:
        # Use thread_id + last message (the new user message) for better coalescing
        # This prevents key changes when conversation history updates
        last_msg = messages[-1] if messages else {}
        payload = {"p": provider, "m": model, "t": thread_id, "msg": last_msg}
    else:
        # Fallback to full conversation (for backwards compatibility)
        payload = {"p": provider, "m": model, "msgs": messages}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()

