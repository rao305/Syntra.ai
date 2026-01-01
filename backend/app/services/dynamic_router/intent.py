"""Router intent classification using LLM."""
from typing import Literal, Optional
from dataclasses import dataclass
import json
import os
from app.adapters.openai_adapter import call_openai

import logging
logger = logging.getLogger(__name__)


TaskType = Literal[
    "generic_chat",
    "web_research",
    "deep_reasoning",
    "coding",
    "math",
    "summarization",
    "document_analysis",
    "creative_writing",
]


Priority = Literal["quality", "speed", "cost"]


@dataclass
class RouterIntent:
    """Structured intent from router LLM."""

    task_type: TaskType
    requires_web: bool
    requires_tools: bool
    priority: Priority
    estimated_input_tokens: int


ROUTER_SYSTEM_PROMPT = """You are the routing brain for a multi-model AI system.

Your job:
- Read the user's latest message (plus a short summary of context).
- Decide what kind of task this is.
- Decide whether it needs live web/search.
- Decide if we should prioritize quality, speed, or cost.
- Roughly estimate how many tokens the input will be.

Respond ONLY as strict JSON, no explanations.

JSON schema:
{
  "taskType": "generic_chat" | "web_research" | "deep_reasoning" | "coding" | "math" | "summarization" | "document_analysis" | "creative_writing",
  "requiresWeb": boolean,
  "requiresTools": boolean,
  "priority": "quality" | "speed" | "cost",
  "estimatedInputTokens": number
}

Guidelines:
- If the user asks for "search", "latest", "today", "news", "papers", or external facts, set "taskType": "web_research" and "requiresWeb": true.
- If the user asks for code, tests, refactors, or debugging, use "coding".
- If the question includes formulas, proofs, or calculations, use "math".
- If the user wants a long explanation, strategy, or multi-step plan, use "deep_reasoning".
- If they paste long text and want a summary or rewrite, use "summarization" or "document_analysis".
- "priority":
  - Use "quality" for complex reasoning, coding, or important decisions.
  - Use "speed" for short casual questions.
  - Use "cost" only if the user explicitly mentions saving money or cost.

Remember: output valid JSON only."""


async def get_router_intent(
    user_message: str, context_summary: str = "", api_key: Optional[str] = None
) -> RouterIntent:
    """
    Call router LLM to classify the task.

    Args:
        user_message: The user's message
        context_summary: Optional summary of conversation context
        api_key: OpenAI API key (if None, uses env var)

    Returns:
        RouterIntent with task classification
    """
    if api_key is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")

    # Build the prompt
    prompt_content = json.dumps(
        {
            "contextSummary": context_summary,
            "userMessage": user_message,
        }
    )

    messages = [
        {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
        {"role": "user", "content": prompt_content},
    ]

    try:
        # Call GPT-4o-mini as router
        response = await call_openai(
            messages=messages,
            model="gpt-4o-mini",
            api_key=api_key,
            temperature=0,
            max_tokens=200,
        )

        raw_content = response.content.strip()

        # Try to extract JSON from the response
        # Sometimes LLM wraps JSON in markdown code blocks
        if "```json" in raw_content:
            raw_content = raw_content.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_content:
            raw_content = raw_content.split("```")[1].split("```")[0].strip()

        parsed = json.loads(raw_content)

        # Map to RouterIntent
        intent = RouterIntent(
            task_type=parsed.get("taskType", "generic_chat"),
            requires_web=parsed.get("requiresWeb", False),
            requires_tools=parsed.get("requiresTools", False),
            priority=parsed.get("priority", "quality"),
            estimated_input_tokens=parsed.get("estimatedInputTokens", len(user_message) // 4),
        )

        # Sanitize estimated tokens
        if intent.estimated_input_tokens <= 0:
            intent.estimated_input_tokens = max(100, len(user_message) // 4)

        return intent

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        # Fallback to safe defaults
        logger.error("⚠️ Router LLM parsing error: {e}, using defaults")
        return RouterIntent(
            task_type="generic_chat",
            requires_web=False,
            requires_tools=False,
            priority="quality",
            estimated_input_tokens=max(100, len(user_message) // 4),
        )











