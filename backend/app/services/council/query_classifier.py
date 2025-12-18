"""
Query Complexity Classification System

Classifies queries into 5 complexity levels to ensure appropriate depth of response.
"""

import re
from typing import Dict, Tuple
from enum import IntEnum

from app.models.provider_key import ProviderType
from app.services.provider_dispatch import call_provider_adapter

import logging
logger = logging.getLogger(__name__)


class QueryComplexity(IntEnum):
    """Query complexity levels."""
    SIMPLE_FACTUAL = 1       # Direct factual questions
    EXPLANATORY = 2          # How/why questions requiring explanation
    TECHNICAL_IMPL = 3       # Implementation tasks with code
    RESEARCH_ANALYSIS = 4    # Comparative analysis, research synthesis
    RESEARCH_GRADE = 5       # Formal proofs, rigorous derivations


COMPLEXITY_EXAMPLES = {
    QueryComplexity.SIMPLE_FACTUAL: [
        "What is the capital of France?",
        "When was Python first released?",
        "What does API stand for?",
    ],
    QueryComplexity.EXPLANATORY: [
        "How does gradient descent work?",
        "Why do we use attention mechanisms in transformers?",
        "Explain the difference between supervised and unsupervised learning",
    ],
    QueryComplexity.TECHNICAL_IMPL: [
        "Write a function to detect cycles in a linked list",
        "Implement a REST API for user authentication",
        "Create a React component for file upload with progress",
    ],
    QueryComplexity.RESEARCH_ANALYSIS: [
        "Compare transformer architectures for time series forecasting",
        "Analyze the trade-offs between microservices and monolithic architecture",
        "What are the latest advances in few-shot learning?",
    ],
    QueryComplexity.RESEARCH_GRADE: [
        "Prove convergence properties of overparameterized neural networks",
        "Derive the backpropagation algorithm from first principles",
        "Formally prove the correctness of the Bellman optimality equation",
    ],
}


COMPLEXITY_INDICATORS = {
    # Level 5 indicators
    "research_grade": [
        r"\b(prove|disprove|theorem|lemma|corollary|proposition)\b",
        r"\b(derive|derivation|rigorous|formal proof|mathematical proof)\b",
        r"\b(convergence properties|asymptotic|complexity bound)\b",
        r"\b(show that|demonstrate that|establish that)\b.*\b(holds|converges|diverges)\b",
        r"\b(necessary and sufficient conditions?)\b",
    ],
    # Level 4 indicators
    "research_analysis": [
        r"\b(compare|contrast|analyze|evaluate|assess)\b.*\b(approaches|methods|architectures)\b",
        r"\b(trade-?offs?|advantages and disadvantages)\b",
        r"\b(state[- ]of[- ]the[- ]art|latest research|recent advances)\b",
        r"\b(comprehensive analysis|in-depth study)\b",
        r"\b(survey|literature review)\b",
    ],
    # Level 3 indicators
    "technical_impl": [
        r"\b(write|implement|create|build|code|develop)\b.*\b(function|class|component|api|system)\b",
        r"\b(algorithm implementation|data structure)\b",
        r"\b(with tests?|test cases?)\b",
        r"\b(complete working|production-ready|fully functional)\b",
    ],
    # Level 2 indicators
    "explanatory": [
        r"\b(how does|why does|explain|what is the difference)\b",
        r"\b(what are the steps|walk me through)\b",
        r"\b(in simple terms|eli5|explain like)\b",
    ],
}


def classify_query_heuristic(query: str) -> int:
    """
    Fast heuristic-based classification using regex patterns.

    Args:
        query: User query text

    Returns:
        Complexity level (1-5)
    """
    query_lower = query.lower()

    # Check Level 5 (research-grade) indicators
    for pattern in COMPLEXITY_INDICATORS["research_grade"]:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return QueryComplexity.RESEARCH_GRADE

    # Check Level 4 (research/analysis) indicators
    for pattern in COMPLEXITY_INDICATORS["research_analysis"]:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return QueryComplexity.RESEARCH_ANALYSIS

    # Check Level 3 (technical implementation) indicators
    for pattern in COMPLEXITY_INDICATORS["technical_impl"]:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return QueryComplexity.TECHNICAL_IMPL

    # Check Level 2 (explanatory) indicators
    for pattern in COMPLEXITY_INDICATORS["explanatory"]:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return QueryComplexity.EXPLANATORY

    # Default to simple factual if no indicators found
    # But check query length as additional heuristic
    if len(query.split()) < 10:
        return QueryComplexity.SIMPLE_FACTUAL
    else:
        return QueryComplexity.EXPLANATORY


async def classify_query_with_llm(
    query: str,
    api_keys: Dict[str, str]
) -> Tuple[int, str]:
    """
    LLM-based classification for more accurate results.

    Args:
        query: User query text
        api_keys: API keys for LLM providers

    Returns:
        Tuple of (complexity_level, reasoning)
    """
    classification_prompt = f"""Classify the following query into one of 5 complexity levels:

LEVEL 1 — SIMPLE FACTUAL
Example: "What is the capital of France?"
Characteristics: Direct factual questions, single fact answer, no explanation needed

LEVEL 2 — EXPLANATORY
Example: "How does gradient descent work?"
Characteristics: Requires explanation, examples helpful, 200-500 words expected

LEVEL 3 — TECHNICAL IMPLEMENTATION
Example: "Write a function to detect cycles in a linked list."
Characteristics: Code implementation required, complete working solution, tests, complexity analysis

LEVEL 4 — RESEARCH/ANALYSIS
Example: "Compare transformer architectures for time series forecasting."
Characteristics: Multiple sources needed, quantitative comparisons, nuanced analysis, 1000+ words

LEVEL 5 — RESEARCH-GRADE/EXPERT
Example: "Prove convergence properties of overparameterized neural networks."
Characteristics: Formal proofs/derivations, rigorous mathematics, citations to papers, experiments, 2000+ words

Query: {query}

Respond in JSON format:
{{
    "level": 1-5,
    "reasoning": "Brief explanation of why this level",
    "key_indicators": ["indicator1", "indicator2"]
}}
"""

    try:
        response = await call_provider_adapter(
            provider=ProviderType.OPENAI,
            model="gpt-4o-mini",  # Fast and cheap for classification
            messages=[{"role": "user", "content": classification_prompt}],
            api_key=api_keys.get("openai", ""),
            max_tokens=200,
        )

        # Parse JSON response
        import json
        response_text = response.content
        result = json.loads(response_text)
        level = int(result.get("level", 3))
        reasoning = result.get("reasoning", "")

        # Validate level is in range
        if not (1 <= level <= 5):
            level = 3  # Default to medium complexity

        return level, reasoning

    except Exception as e:
        # Fall back to heuristic if LLM fails
        logger.info("LLM classification failed: {e}, using heuristic")
        level = classify_query_heuristic(query)
        return level, "Heuristic classification (LLM failed)"


async def classify_query(
    query: str,
    api_keys: Dict[str, str] = None,
    use_llm: bool = True
) -> Tuple[int, str]:
    """
    Classify query complexity level.

    Args:
        query: User query text
        api_keys: Optional API keys for LLM-based classification
        use_llm: Whether to use LLM (True) or heuristic (False)

    Returns:
        Tuple of (complexity_level, reasoning)
    """
    if use_llm and api_keys:
        return await classify_query_with_llm(query, api_keys)
    else:
        level = classify_query_heuristic(query)
        reasoning = f"Heuristic classification based on query patterns"
        return level, reasoning


def get_expected_response_characteristics(complexity: int) -> Dict[str, any]:
    """
    Get expected response characteristics for a complexity level.

    Args:
        complexity: Complexity level (1-5)

    Returns:
        Dictionary with expected characteristics
    """
    characteristics = {
        QueryComplexity.SIMPLE_FACTUAL: {
            "min_words": 10,
            "max_words": 100,
            "require_citations": False,
            "require_code": False,
            "require_math": False,
            "expected_sections": 1,
            "depth_score_threshold": 3.0,
        },
        QueryComplexity.EXPLANATORY: {
            "min_words": 200,
            "max_words": 500,
            "require_citations": False,
            "require_code": False,
            "require_math": False,
            "expected_sections": 2,
            "depth_score_threshold": 5.0,
        },
        QueryComplexity.TECHNICAL_IMPL: {
            "min_words": 300,
            "max_words": 1000,
            "require_citations": False,
            "require_code": True,
            "require_math": False,
            "expected_sections": 3,
            "depth_score_threshold": 7.0,
            "code_quality_checks": [
                "no_placeholders",
                "complete_imports",
                "runnable",
                "test_cases",
            ],
        },
        QueryComplexity.RESEARCH_ANALYSIS: {
            "min_words": 1000,
            "max_words": 3000,
            "require_citations": True,
            "require_code": False,
            "require_math": False,
            "expected_sections": 5,
            "depth_score_threshold": 8.0,
            "min_citations": 5,
        },
        QueryComplexity.RESEARCH_GRADE: {
            "min_words": 2000,
            "max_words": 5000,
            "require_citations": True,
            "require_code": True,
            "require_math": True,
            "expected_sections": 6,
            "depth_score_threshold": 9.0,
            "min_citations": 10,
            "code_quality_checks": [
                "no_placeholders",
                "complete_imports",
                "runnable",
                "experiments",
                "results_analysis",
            ],
            "math_requirements": [
                "formal_definitions",
                "theorem_statements",
                "proof_sketches",
            ],
        },
    }

    return characteristics.get(complexity, characteristics[QueryComplexity.EXPLANATORY])
