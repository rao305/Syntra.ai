"""
Agent module - System prompts and configurations for all agents.
"""

from .architect import ARCHITECT_PROMPT
from .data_engineer import DATA_ENGINEER_PROMPT
from .researcher import RESEARCHER_PROMPT
from .red_teamer import RED_TEAMER_PROMPT
from .optimizer import OPTIMIZER_PROMPT
from .synthesizer import SYNTHESIZER_PROMPT
from .judge import get_judge_prompt

__all__ = [
    "ARCHITECT_PROMPT",
    "DATA_ENGINEER_PROMPT",
    "RESEARCHER_PROMPT",
    "RED_TEAMER_PROMPT",
    "OPTIMIZER_PROMPT",
    "SYNTHESIZER_PROMPT",
    "get_judge_prompt",
]
