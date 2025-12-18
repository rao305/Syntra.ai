"""Query classification for intelligent LLM routing.

This service analyzes user queries to determine:
1. Query type/domain (factual, reasoning, code, creative, etc.)
2. Complexity level
3. Recommended provider and model

Based on the Collaborative Memory paper's concept of domain-specialist agents.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

from app.models.provider_key import ProviderType


class QueryType(str, Enum):
    """Types of queries for classification."""

    FACTUAL = "factual"  # Needs web search, citations, current info
    REASONING = "reasoning"  # Complex logic, chain-of-thought
    CODE = "code"  # Programming, debugging
    CREATIVE = "creative"  # Writing, brainstorming
    MULTILINGUAL = "multilingual"  # Non-English queries
    SIMPLE = "simple"  # Quick Q&A
    ANALYSIS = "analysis"  # Data analysis, comparison
    CONVERSATION = "conversation"  # Casual chat


class ComplexityLevel(str, Enum):
    """Query complexity assessment."""

    LOW = "low"  # Simple, quick answer
    MEDIUM = "medium"  # Moderate reasoning required
    HIGH = "high"  # Complex, multi-step reasoning


@dataclass
class QueryClassification:
    """Result of query classification."""

    query_type: QueryType
    complexity: ComplexityLevel
    recommended_provider: ProviderType
    recommended_model: str
    reason: str
    confidence: float  # 0.0 to 1.0


class QueryClassifier:
    """Classifies queries to determine optimal LLM routing."""

    # Keywords for different query types
    FACTUAL_KEYWORDS = [
        "what is", "who is", "when did", "where is", "latest", "current",
        "news", "recent", "update", "happening", "search", "find",
        "what happened", "define", "explain", "tell me about",
        # Additional factual keywords
        "how to", "why does", "how does", "what are", "what does",
        "which", "where", "when", "who", "how much", "how many",
        "facts", "information", "details", "summary", "overview",
        "statistics", "data", "research", "study", "analysis"
    ]

    REASONING_KEYWORDS = [
        "analyze", "compare", "evaluate", "why", "how does", "reasoning",
        "logic", "prove", "deduce", "infer", "conclude", "justify",
        "chain of thought", "step by step", "think through"
    ]

    CODE_KEYWORDS = [
        "code", "program", "debug", "function", "class", "algorithm",
        "python", "javascript", "java", "c++", "rust", "sql",
        "api", "implement", "refactor", "bug", "error", "syntax"
    ]

    CREATIVE_KEYWORDS = [
        "write", "create", "story", "poem", "essay", "brainstorm",
        "creative", "imagine", "invent", "design", "compose"
    ]

    ANALYSIS_KEYWORDS = [
        "analyze", "comparison", "versus", "vs", "compare", "contrast",
        "pros and cons", "advantages", "disadvantages", "evaluate",
        "assess", "review", "examine"
    ]

    # Language patterns for multilingual detection
    CHINESE_PATTERN = re.compile(r'[\u4e00-\u9fff]+')
    JAPANESE_PATTERN = re.compile(r'[\u3040-\u309f\u30a0-\u30ff]+')
    KOREAN_PATTERN = re.compile(r'[\uac00-\ud7af]+')
    ARABIC_PATTERN = re.compile(r'[\u0600-\u06ff]+')

    def classify(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> QueryClassification:
        """
        Classify a query to determine optimal LLM routing.

        Args:
            query: The user's query
            conversation_history: Previous messages for context

        Returns:
            QueryClassification with routing recommendation
        """
        query_lower = query.lower()

        # PRIORITY 1: Check if this is a translation/localization request
        # (translation should ALWAYS route to Kimi regardless of other task type)
        if self._is_translation_request(query_lower):
            return self._classify_translation(query)

        # PRIORITY 2: Detect query type based on keywords (CODE, FACTUAL, REASONING, etc.)
        # This works across languages (e.g., "python" keyword in Chinese query still matches)
        query_type = self._detect_query_type(query_lower)

        # Assess complexity
        complexity = self._assess_complexity(query, conversation_history)

        # Get routing recommendation based on task type
        provider, model, reason = self._get_routing_recommendation(
            query_type, complexity, query_lower
        )

        # Calculate confidence
        confidence = self._calculate_confidence(query_lower, query_type)

        return QueryClassification(
            query_type=query_type,
            complexity=complexity,
            recommended_provider=provider,
            recommended_model=model,
            reason=reason,
            confidence=confidence
        )

    def _is_translation_request(self, query: str) -> bool:
        """Check if query is specifically asking for translation/localization."""
        query_lower = query.lower()
        translation_keywords = [
            "translate", "translation", "translate to", "translate from",
            "翻译", "翻譯", "번역", "ترجمة",
            "localize", "localization", "bilingual content", "multilingual content"
        ]
        return any(kw in query_lower for kw in translation_keywords)

    def _classify_translation(self, query: str) -> QueryClassification:
        """Handle translation/localization requests."""
        query_lower = query.lower()

        # Kimi is excellent for translation, especially with CJK languages
        # Can handle large context windows (128k) for document translation
        return QueryClassification(
            query_type=QueryType.MULTILINGUAL,
            complexity=ComplexityLevel.MEDIUM,
            recommended_provider=ProviderType.KIMI,
            recommended_model="moonshot-v1-32k",
            reason="Translation request - Kimi specializes in bilingual content with 128k context",
            confidence=0.95
        )

    def _classify_multilingual(self, query: str) -> QueryClassification:
        """
        Handle multilingual queries (Chinese, Japanese, etc.).

        NOTE: This should only be called for queries with non-English characters
        but NOT translation requests (those are handled by _classify_translation).

        Route based on task type (CODE, FACTUAL, etc.) within that language,
        not automatically to Kimi.
        """
        # If Chinese characters detected, lean toward Kimi with high confidence
        # but only if no specific task type detected
        if self.CHINESE_PATTERN.search(query):
            return QueryClassification(
                query_type=QueryType.MULTILINGUAL,
                complexity=ComplexityLevel.MEDIUM,
                recommended_provider=ProviderType.KIMI,
                recommended_model="moonshot-v1-32k",
                reason="Chinese language query - Kimi specializes in Chinese with 128k context",
                confidence=0.90
            )

        # For other multilingual content, use Gemini's strong multilingual support
        return QueryClassification(
            query_type=QueryType.MULTILINGUAL,
            complexity=ComplexityLevel.MEDIUM,
            recommended_provider=ProviderType.GEMINI,
            recommended_model="gemini-2.5-pro",
            reason="Multilingual query detected - Gemini has strong world language support",
            confidence=0.85
        )

    def _detect_query_type(self, query_lower: str) -> QueryType:
        """Detect the primary type of query."""
        scores = {
            QueryType.FACTUAL: self._count_keywords(query_lower, self.FACTUAL_KEYWORDS),
            QueryType.REASONING: self._count_keywords(query_lower, self.REASONING_KEYWORDS),
            QueryType.CODE: self._count_keywords(query_lower, self.CODE_KEYWORDS),
            QueryType.CREATIVE: self._count_keywords(query_lower, self.CREATIVE_KEYWORDS),
            QueryType.ANALYSIS: self._count_keywords(query_lower, self.ANALYSIS_KEYWORDS),
        }

        # Find highest score
        max_score = max(scores.values())

        if max_score == 0:
            # No keywords matched - analyze query structure for better classification
            return self._classify_by_structure(query_lower)

        # Return type with highest score
        for query_type, score in scores.items():
            if score == max_score:
                return query_type

        return QueryType.SIMPLE

    def _classify_by_structure(self, query_lower: str) -> QueryType:
        """Classify queries based on sentence structure when no keywords match."""
        # Check for question patterns (often factual)
        question_words = ['what', 'who', 'where', 'when', 'why', 'how', 'which']
        if any(query_lower.startswith(word) for word in question_words):
            return QueryType.FACTUAL

        # Check for explanatory requests
        explanatory_phrases = ['explain', 'describe', 'tell me', 'can you']
        if any(phrase in query_lower for phrase in explanatory_phrases):
            return QueryType.FACTUAL

        # Check for comparative language
        comparative_words = ['versus', 'vs', 'compared to', 'better than', 'worse than']
        if any(word in query_lower for word in comparative_words):
            return QueryType.ANALYSIS

        # Default to simple for casual conversation
        return QueryType.SIMPLE

    def _count_keywords(self, query_lower: str, keywords: List[str]) -> int:
        """Count how many keywords appear in the query."""
        return sum(1 for keyword in keywords if keyword in query_lower)

    def _assess_complexity(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> ComplexityLevel:
        """Assess the complexity of the query."""
        # Simple heuristics
        word_count = len(query.split())

        # Check for complexity indicators
        has_multiple_questions = query.count('?') > 1
        has_conditions = any(word in query.lower() for word in ['if', 'when', 'unless', 'given'])
        has_comparison = any(word in query.lower() for word in ['compare', 'versus', 'vs', 'difference'])

        # Long context increases complexity
        long_context = conversation_history and len(conversation_history) > 3

        complexity_score = 0

        if word_count > 50:
            complexity_score += 2
        elif word_count > 20:
            complexity_score += 1

        if has_multiple_questions:
            complexity_score += 1
        if has_conditions:
            complexity_score += 1
        if has_comparison:
            complexity_score += 1
        if long_context:
            complexity_score += 1

        if complexity_score >= 4:
            return ComplexityLevel.HIGH
        elif complexity_score >= 2:
            return ComplexityLevel.MEDIUM
        else:
            return ComplexityLevel.LOW

    def _get_routing_recommendation(
        self,
        query_type: QueryType,
        complexity: ComplexityLevel,
        query_lower: str
    ) -> Tuple[ProviderType, str, str]:
        """
        Get provider and model recommendation based on query type and complexity.

        ROUTING STRATEGY: Use what each model is BEST at
        - OpenAI: Best for code, reasoning, creative writing
        - Perplexity: Best for factual queries (has web search & citations)
        - Gemini: Best for simple queries, speed, large context
        - Kimi: Best for multilingual content

        Cost is secondary - quality and capability come first.

        Returns: (provider, model, reason)
        """
        # FACTUAL queries: Perplexity is BEST (web search + citations)
        if query_type == QueryType.FACTUAL:
            if complexity == ComplexityLevel.HIGH:
                return (
                    ProviderType.PERPLEXITY,
                    "sonar-pro",
                    "Factual query - Perplexity Sonar Pro excels with web search and citations"
                )
            else:
                return (
                    ProviderType.PERPLEXITY,
                    "sonar",
                    "Factual query - Perplexity Sonar provides real-time web search"
                )

        # CODE queries: OpenAI is BEST at code generation
        if query_type == QueryType.CODE:
            if complexity == ComplexityLevel.HIGH:
                return (
                    ProviderType.OPENAI,
                    "gpt-4o-mini",
                    "Code generation - OpenAI excels at complex programming tasks"
                )
            else:
                # Even simple code - OpenAI is better at code than Gemini
                return (
                    ProviderType.OPENAI,
                    "gpt-4o-mini",
                    "Code generation - OpenAI's strong programming capabilities"
                )

        # CREATIVE queries: OpenAI is BEST at creative writing
        if query_type == QueryType.CREATIVE:
            return (
                ProviderType.OPENAI,
                "gpt-4o-mini",
                "Creative writing - OpenAI excels at storytelling and creative content"
            )

        # REASONING queries: OpenAI is BEST at logical reasoning
        if query_type == QueryType.REASONING:
            if complexity == ComplexityLevel.HIGH:
                return (
                    ProviderType.OPENAI,
                    "gpt-4o-mini",
                    "Complex reasoning - OpenAI's superior logical capabilities"
                )
            else:
                return (
                    ProviderType.OPENAI,
                    "gpt-4o-mini",
                    "Reasoning task - OpenAI's strong analytical abilities"
                )

        # ANALYSIS queries: OpenAI is BEST at structured analysis
        if query_type == QueryType.ANALYSIS:
            return (
                ProviderType.OPENAI,
                "gpt-4o-mini",
                "Analysis task - OpenAI's structured reasoning and depth"
            )

        # SIMPLE queries: Balance between OpenAI and Gemini, favor OpenAI for quality
        if query_type == QueryType.SIMPLE or query_type == QueryType.CONVERSATION:
            # Alternate between OpenAI and Gemini for simple queries
            # OpenAI gives better quality, Gemini gives better speed/cost
            import random
            if random.random() < 0.6:  # 60% OpenAI, 40% Gemini for better quality
                return (
                    ProviderType.OPENAI,
                    "gpt-4o-mini",
                    "Simple query - OpenAI for reliable responses"
                )
            else:
                return (
                    ProviderType.GEMINI,
                    "gemini-2.5-flash",
                    "Simple query - Gemini Flash for quick responses"
                )

        # Default fallback: OpenAI for general capability
        return (
            ProviderType.OPENAI,
            "gpt-4o-mini",
            "General query - OpenAI for balanced performance"
        )

    def _calculate_confidence(self, query_lower: str, query_type: QueryType) -> float:
        """Calculate confidence score for the classification."""
        # Count matching keywords for the detected type
        keyword_lists = {
            QueryType.FACTUAL: self.FACTUAL_KEYWORDS,
            QueryType.REASONING: self.REASONING_KEYWORDS,
            QueryType.CODE: self.CODE_KEYWORDS,
            QueryType.CREATIVE: self.CREATIVE_KEYWORDS,
            QueryType.ANALYSIS: self.ANALYSIS_KEYWORDS,
        }

        if query_type not in keyword_lists:
            return 0.5  # Moderate confidence for simple queries

        keywords = keyword_lists[query_type]
        matches = self._count_keywords(query_lower, keywords)

        # Higher matches = higher confidence
        if matches >= 3:
            return 0.95
        elif matches == 2:
            return 0.85
        elif matches == 1:
            return 0.70
        else:
            return 0.60


# Singleton instance
query_classifier = QueryClassifier()
