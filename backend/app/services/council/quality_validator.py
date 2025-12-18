"""
Quality Validator Agent

Validates responses against quality criteria and complexity requirements.
Scores responses on substance, completeness, depth, and accuracy.
"""

import re
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from app.services.council.base import run_agent
from app.services.council.query_classifier import (
    QueryComplexity,
    get_expected_response_characteristics
)

import logging
logger = logging.getLogger(__name__)


@dataclass
class QualityScores:
    """Quality scores for a response."""
    substance_score: float  # 0-10: Ratio of actual content vs metadata
    completeness_score: float  # 0-10: All sub-questions answered
    depth_score: float  # 0-10: Appropriate depth for complexity
    accuracy_score: float  # 0-10: Correctness of claims and code
    overall_score: float  # 0-10: Weighted average
    quality_gate_passed: bool  # True if all scores >= 7

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "substance_score": self.substance_score,
            "completeness_score": self.completeness_score,
            "depth_score": self.depth_score,
            "accuracy_score": self.accuracy_score,
            "overall_score": self.overall_score,
            "quality_gate_passed": self.quality_gate_passed,
        }


@dataclass
class QualityValidationResult:
    """Result of quality validation."""
    scores: QualityScores
    gaps_identified: List[str]
    additional_content: Optional[str]
    validation_reasoning: str
    needs_revision: bool


QUALITY_VALIDATOR_PROMPT = """
You are a Quality Validator Agent for Syntra's collaboration system.

Your job is to rigorously evaluate the final response and assign scores based on these criteria:

=============================================================================
SCORING CRITERIA
=============================================================================

1. SUBSTANCE_SCORE (0-10): Ratio of Actual Content vs Metadata
   - 10: 90%+ actual explanations, code, proofs, analysis
   - 7-9: 70-89% substantive content
   - 4-6: 50-69% substantive content
   - 0-3: <50% substantive content, mostly boilerplate/metadata

   RED FLAGS (auto-score ≤3):
   - Response is mostly ownership tables, file structures, or checklists
   - Uses "✅" checkboxes without actual content
   - Placeholder code (pass, # TODO, # Placeholder)
   - File structure boilerplate (main.py, config.py) without implementations

2. COMPLETENESS_SCORE (0-10): All Sub-Questions Answered
   - 10: All sub-questions fully addressed
   - 7-9: Most sub-questions addressed, minor gaps
   - 4-6: Several sub-questions missing or superficial
   - 0-3: Major gaps, many sub-questions unanswered

3. DEPTH_SCORE (0-10): Appropriate Depth for Query Complexity
   Query Complexity Level: {query_complexity}/5
   Expected Characteristics: {expected_characteristics}

   For Level 5 (Research-Grade):
   - 10: Formal definitions, theorem statements, proof sketches, working code, experiments
   - 7-9: Most elements present, some depth missing
   - 4-6: Superficial coverage of complex topics
   - 0-3: No rigorous treatment

   For Level 3 (Technical Implementation):
   - 10: Complete working code, no placeholders, test cases, complexity analysis
   - 7-9: Working code with minor gaps
   - 4-6: Code with placeholders or missing tests
   - 0-3: Pseudocode or non-functional code

4. ACCURACY_SCORE (0-10): Correctness of Claims and Code
   - 10: All statements accurate, code runs correctly
   - 7-9: Minor inaccuracies or edge case bugs
   - 4-6: Some incorrect claims or broken code
   - 0-3: Major errors, misinformation, or non-functional code

=============================================================================
YOUR TASK
=============================================================================

Review the response below and:
1. Assign scores for each criterion (0-10)
2. Identify specific gaps if any score < 7
3. If gaps exist, generate additional content to fill them (don't just list gaps)
4. Provide reasoning for your scores

Original Query: {query}

Response to Validate:
{response}

=============================================================================
OUTPUT FORMAT (JSON)
=============================================================================

{{
    "scores": {{
        "substance_score": 0-10,
        "completeness_score": 0-10,
        "depth_score": 0-10,
        "accuracy_score": 0-10
    }},
    "reasoning": {{
        "substance": "Why this score...",
        "completeness": "Why this score...",
        "depth": "Why this score...",
        "accuracy": "Why this score..."
    }},
    "gaps_identified": [
        "Specific gap 1",
        "Specific gap 2"
    ],
    "additional_content": "ONLY if gaps exist, provide the missing content here. If no gaps, leave empty.",
    "needs_revision": true/false
}}

CRITICAL: If additional_content is provided, it must be ACTUAL CONTENT (code, proofs, explanations),
NOT just instructions like "Add a proof here" or "Include more examples".
"""


def analyze_response_heuristics(response: str, query_complexity: int) -> Dict[str, float]:
    """
    Fast heuristic-based scoring before LLM validation.

    Args:
        response: Response text to analyze
        query_complexity: Query complexity level (1-5)

    Returns:
        Dictionary with heuristic scores
    """
    # Calculate basic metrics
    total_chars = len(response)
    lines = response.split('\n')

    # Count metadata indicators (ownership, checkboxes, etc.)
    metadata_patterns = [
        r'✅.*?(?=\n)',
        r'##\s*Ownership',
        r'##\s*File\s*Structure',
        r'##\s*Compliance',
        r'\|\s*File\s*\|\s*Owner\s*\|',
    ]
    metadata_chars = sum(
        len(match.group())
        for pattern in metadata_patterns
        for match in re.finditer(pattern, response, re.IGNORECASE)
    )

    # Count placeholder code
    placeholder_patterns = [
        r'\bpass\s*(?=\n)',
        r'#\s*TODO',
        r'#\s*Placeholder',
        r'#\s*Implementation\s*needed',
    ]
    placeholder_count = sum(
        len(re.findall(pattern, response, re.IGNORECASE))
        for pattern in placeholder_patterns
    )

    # Count code blocks
    code_blocks = re.findall(r'```[\s\S]*?```', response)
    code_chars = sum(len(block) for block in code_blocks)

    # Count citations (Author et al., Year)
    citations = re.findall(r'\b[A-Z][a-z]+\s+et\s+al\.\s+\(\d{4}\)', response)
    citation_count = len(citations)

    # Count mathematical notation
    math_patterns = [
        r'\$.*?\$',  # Inline math
        r'\$\$[\s\S]*?\$\$',  # Display math
        r'\\[a-zA-Z]+\{',  # LaTeX commands
        r'[≤≥≈∈∑∫∇]',  # Math symbols
    ]
    math_count = sum(
        len(re.findall(pattern, response))
        for pattern in math_patterns
    )

    # Count headings
    headings = re.findall(r'^#+\s+.+$', response, re.MULTILINE)
    heading_count = len(headings)

    # Calculate heuristic scores
    substance_score = 10.0
    if total_chars > 0:
        metadata_ratio = metadata_chars / total_chars
        substance_score = max(0, 10 - (metadata_ratio * 50))  # Penalize metadata
        if placeholder_count > 0:
            substance_score = min(substance_score, 3.0)  # Heavy penalty for placeholders

    # Depth score based on complexity requirements
    expected = get_expected_response_characteristics(query_complexity)
    word_count = len(response.split())

    depth_score = 5.0  # Start neutral
    if word_count >= expected["min_words"]:
        depth_score += 2.0
    if query_complexity >= 4 and citation_count >= expected.get("min_citations", 0):
        depth_score += 2.0
    if query_complexity >= 3 and expected.get("require_code") and len(code_blocks) > 0:
        depth_score += 1.0
    if query_complexity >= 5 and math_count > 0:
        depth_score += 1.0

    depth_score = min(10.0, depth_score)

    return {
        "substance_score_heuristic": substance_score,
        "depth_score_heuristic": depth_score,
        "metadata_ratio": metadata_ratio if total_chars > 0 else 0,
        "placeholder_count": placeholder_count,
        "word_count": word_count,
        "citation_count": citation_count,
        "code_block_count": len(code_blocks),
        "math_notation_count": math_count,
        "heading_count": heading_count,
    }


async def validate_response_quality(
    query: str,
    response: str,
    query_complexity: int,
    api_keys: Dict[str, str],
    preferred_provider: str = "openai"
) -> QualityValidationResult:
    """
    Validate response quality using LLM-based scoring.

    Args:
        query: Original user query
        response: Response to validate
        query_complexity: Query complexity level (1-5)
        api_keys: API keys for LLM providers
        preferred_provider: Preferred provider for validation

    Returns:
        QualityValidationResult with scores and identified gaps
    """
    # Get expected characteristics
    expected = get_expected_response_characteristics(query_complexity)

    # First, run heuristic analysis
    heuristics = analyze_response_heuristics(response, query_complexity)

    # If heuristics show obvious failures, skip LLM and return low scores
    if heuristics["placeholder_count"] > 0 or heuristics["substance_score_heuristic"] < 3:
        return QualityValidationResult(
            scores=QualityScores(
                substance_score=heuristics["substance_score_heuristic"],
                completeness_score=3.0,
                depth_score=3.0,
                accuracy_score=5.0,
                overall_score=3.5,
                quality_gate_passed=False,
            ),
            gaps_identified=[
                f"Response contains {heuristics['placeholder_count']} placeholder code blocks",
                f"Metadata ratio too high ({heuristics['metadata_ratio']:.1%})",
                "Response is mostly boilerplate, not substantive content",
            ],
            additional_content=None,
            validation_reasoning="Failed heuristic checks: placeholder code or high metadata ratio",
            needs_revision=True,
        )

    # Format the validation prompt
    validator_prompt = QUALITY_VALIDATOR_PROMPT.format(
        query_complexity=query_complexity,
        expected_characteristics=json.dumps(expected, indent=2),
        query=query,
        response=response,
    )

    try:
        # Call LLM for validation
        validation_response, _ = await run_agent(
            agent_name="quality_validator",
            system_prompt=validator_prompt,
            user_message="Validate this response and provide scores.",
            api_keys=api_keys,
            preferred_provider=preferred_provider,
            max_tokens=2000,
        )

        # Parse JSON response
        # Extract JSON from markdown code blocks if present
        json_match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', validation_response)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON object directly
            json_match = re.search(r'\{[\s\S]*\}', validation_response)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError("No JSON found in validation response")

        result = json.loads(json_str)

        # Extract scores
        scores_dict = result.get("scores", {})
        substance = float(scores_dict.get("substance_score", 5.0))
        completeness = float(scores_dict.get("completeness_score", 5.0))
        depth = float(scores_dict.get("depth_score", 5.0))
        accuracy = float(scores_dict.get("accuracy_score", 5.0))

        # Calculate overall score (weighted average)
        overall = (
            substance * 0.3 +
            completeness * 0.3 +
            depth * 0.25 +
            accuracy * 0.15
        )

        # Quality gate: all scores must be >= 7
        quality_gate_passed = all([
            substance >= 7.0,
            completeness >= 7.0,
            depth >= 7.0,
            accuracy >= 7.0,
        ])

        scores = QualityScores(
            substance_score=substance,
            completeness_score=completeness,
            depth_score=depth,
            accuracy_score=accuracy,
            overall_score=overall,
            quality_gate_passed=quality_gate_passed,
        )

        # Extract gaps and additional content
        gaps = result.get("gaps_identified", [])
        additional_content = result.get("additional_content", "")
        needs_revision = result.get("needs_revision", False)

        # Build reasoning summary
        reasoning_dict = result.get("reasoning", {})
        validation_reasoning = "\n".join([
            f"Substance: {reasoning_dict.get('substance', 'N/A')}",
            f"Completeness: {reasoning_dict.get('completeness', 'N/A')}",
            f"Depth: {reasoning_dict.get('depth', 'N/A')}",
            f"Accuracy: {reasoning_dict.get('accuracy', 'N/A')}",
        ])

        return QualityValidationResult(
            scores=scores,
            gaps_identified=gaps,
            additional_content=additional_content if additional_content else None,
            validation_reasoning=validation_reasoning,
            needs_revision=needs_revision,
        )

    except Exception as e:
        logger.info("Quality validation failed: {e}")
        # Return conservative scores on failure
        return QualityValidationResult(
            scores=QualityScores(
                substance_score=5.0,
                completeness_score=5.0,
                depth_score=5.0,
                accuracy_score=5.0,
                overall_score=5.0,
                quality_gate_passed=False,
            ),
            gaps_identified=[f"Validation error: {str(e)}"],
            additional_content=None,
            validation_reasoning=f"Validation failed due to error: {str(e)}",
            needs_revision=True,
        )


def check_code_quality(response: str) -> Tuple[bool, List[str]]:
    """
    Check code quality in response.

    Args:
        response: Response text

    Returns:
        Tuple of (passes, issues)
    """
    issues = []

    # Extract code blocks
    code_blocks = re.findall(r'```(?:python|javascript|typescript|java|cpp|c)?\s*([\s\S]*?)```', response)

    if not code_blocks:
        return True, []  # No code, no code issues

    for i, code in enumerate(code_blocks):
        # Check for placeholders
        if re.search(r'\bpass\s*(?:#.*)?$', code, re.MULTILINE):
            issues.append(f"Code block {i+1}: Contains 'pass' placeholder")
        if re.search(r'#\s*TODO', code, re.IGNORECASE):
            issues.append(f"Code block {i+1}: Contains '# TODO' placeholder")
        if re.search(r'#\s*Placeholder', code, re.IGNORECASE):
            issues.append(f"Code block {i+1}: Contains '# Placeholder'")

        # Check for incomplete imports
        if re.search(r'^import\s+\.\.\.$', code, re.MULTILINE):
            issues.append(f"Code block {i+1}: Incomplete imports (...)")

        # Check for function stubs
        if re.search(r'def\s+\w+\([^)]*\):\s*(?:pass|\.\.\.)\s*$', code, re.MULTILINE):
            issues.append(f"Code block {i+1}: Function stub without implementation")

    passes = len(issues) == 0
    return passes, issues


def check_citations(response: str, min_citations: int = 0) -> Tuple[bool, int]:
    """
    Check if response has sufficient citations.

    Args:
        response: Response text
        min_citations: Minimum required citations

    Returns:
        Tuple of (passes, citation_count)
    """
    # Look for academic citation patterns
    patterns = [
        r'\b[A-Z][a-z]+\s+et\s+al\.\s+\(\d{4}\)',  # Author et al. (Year)
        r'\b[A-Z][a-z]+\s+\(\d{4}\)',  # Author (Year)
        r'\[\d+\]',  # [1] style references
    ]

    citations = set()
    for pattern in patterns:
        matches = re.findall(pattern, response)
        citations.update(matches)

    citation_count = len(citations)
    passes = citation_count >= min_citations

    return passes, citation_count
