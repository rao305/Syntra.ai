"""
Multi-Agent Council Orchestrator Module

A distributed decision-making system leveraging five specialized AI agents
to collaboratively solve complex problems with full traceability.

Supports multiple LLM providers: OpenAI, Perplexity, Gemini, Kimi.
"""

from .orchestrator import CouncilOrchestrator, CouncilConfig, CouncilOutput

__all__ = [
    "CouncilOrchestrator",
    "CouncilConfig",
    "CouncilOutput",
]
