"""
Training dataset for fine-tuning the router model.
Designed to be extensible — add examples for new models easily.
"""

import json
from typing import List, Dict, Any
from dataclasses import dataclass
import random


@dataclass
class RoutingExample:
    """A single training example for the router."""
    query: str
    context: str  # Previous conversation context (optional)
    user_priority: str  # speed, cost, quality, balanced
    expected_model: str
    task_type: str
    complexity: int
    confidence: float
    reasoning: str
    needs_web: bool
    estimated_tokens:  int

    def to_training_format(self, system_prompt: str) -> Dict[str, Any]:
        """Convert to OpenAI fine-tuning format."""
        user_content = f"Query: {self.query}"
        if self. context:
            user_content += f"\nContext: {self.context}"
        user_content += f"\nUser Priority: {self.user_priority}"

        assistant_content = json.dumps({
            "model": self. expected_model,
            "task_type": self.task_type,
            "complexity": self.complexity,
            "confidence": self.confidence,
            "reasoning":  self.reasoning,
            "needs_web": self.needs_web,
            "estimated_tokens": self.estimated_tokens
        })

        return {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
                {"role":  "assistant", "content": assistant_content}
            ]
        }


# =============================================================================
# TRAINING EXAMPLES DATABASE
# =============================================================================

TRAINING_EXAMPLES:  List[RoutingExample] = [

    # =========================================================================
    # SIMPLE QUERIES → gpt-4o-mini
    # =========================================================================

    RoutingExample(
        query="What's the capital of France?",
        context="",
        user_priority="balanced",
        expected_model="gpt-4o-mini",
        task_type="simple_qa",
        complexity=1,
        confidence=0.95,
        reasoning="Simple factual question, cheapest model sufficient",
        needs_web=False,
        estimated_tokens=50
    ),
    RoutingExample(
        query="Hi!  How are you today?",
        context="",
        user_priority="balanced",
        expected_model="gpt-4o-mini",
        task_type="conversation",
        complexity=1,
        confidence=0.98,
        reasoning="Casual greeting, use cheapest model",
        needs_web=False,
        estimated_tokens=30
    ),
    RoutingExample(
        query="Thanks for your help!",
        context="",
        user_priority="balanced",
        expected_model="gpt-4o-mini",
        task_type="conversation",
        complexity=1,
        confidence=0.99,
        reasoning="Simple acknowledgment",
        needs_web=False,
        estimated_tokens=20
    ),
    RoutingExample(
        query="What does 'serendipity' mean?",
        context="",
        user_priority="balanced",
        expected_model="gpt-4o-mini",
        task_type="simple_qa",
        complexity=1,
        confidence=0.95,
        reasoning="Dictionary definition request",
        needs_web=False,
        estimated_tokens=60
    ),
    RoutingExample(
        query="Translate 'Good morning' to Spanish",
        context="",
        user_priority="balanced",
        expected_model="gpt-4o-mini",
        task_type="translation",
        complexity=1,
        confidence=0.94,
        reasoning="Simple translation task",
        needs_web=False,
        estimated_tokens=40
    ),
    RoutingExample(
        query="What's 15% of 340? ",
        context="",
        user_priority="balanced",
        expected_model="gpt-4o-mini",
        task_type="math",
        complexity=1,
        confidence=0.95,
        reasoning="Basic arithmetic",
        needs_web=False,
        estimated_tokens=30
    ),
    RoutingExample(
        query="Give me a random fun fact",
        context="",
        user_priority="balanced",
        expected_model="gpt-4o-mini",
        task_type="simple_qa",
        complexity=1,
        confidence=0.90,
        reasoning="Simple entertainment request",
        needs_web=False,
        estimated_tokens=100
    ),
    RoutingExample(
        query="What time is it in Tokyo?",
        context="",
        user_priority="balanced",
        expected_model="gpt-4o-mini",
        task_type="simple_qa",
        complexity=1,
        confidence=0.88,
        reasoning="Simple time zone question",
        needs_web=False,
        estimated_tokens=40
    ),
    RoutingExample(
        query="Can you help me? ",
        context="",
        user_priority="balanced",
        expected_model="gpt-4o-mini",
        task_type="conversation",
        complexity=1,
        confidence=0.85,
        reasoning="Vague request, use cheap model to clarify",
        needs_web=False,
        estimated_tokens=50
    ),
    RoutingExample(
        query="Tell me a joke",
        context="",
        user_priority="balanced",
        expected_model="gpt-4o-mini",
        task_type="conversation",
        complexity=1,
        confidence=0.92,
        reasoning="Simple entertainment request",
        needs_web=False,
        estimated_tokens=80
    ),

    # =========================================================================
    # CODING TASKS → gpt-4o or kimi-k2
    # =========================================================================

    RoutingExample(
        query="Write a Python function to check if a string is a palindrome",
        context="",
        user_priority="balanced",
        expected_model="gpt-4o",
        task_type="coding",
        complexity=2,
        confidence=0.90,
        reasoning="Basic coding task, reliable model preferred",
        needs_web=False,
        estimated_tokens=150
    ),
    RoutingExample(
        query="Implement a distributed rate limiter in Go that handles 1M requests per second with Redis backend",
        context="",
        user_priority="quality",
        expected_model="gpt-4o",
        task_type="coding",
        complexity=5,
        confidence=0.95,
        reasoning="Complex distributed systems coding, needs top model",
        needs_web=False,
        estimated_tokens=2000
    ),
    RoutingExample(
        query="Debug this React useEffect that causes infinite re-renders:  [code snippet]",
        context="",
        user_priority="balanced",
        expected_model="gpt-4o",
        task_type="coding",
        complexity=4,
        confidence=0.91,
        reasoning="Debugging requires careful analysis",
        needs_web=False,
        estimated_tokens=500
    ),
    RoutingExample(
        query="Write a simple hello world in Python",
        context="",
        user_priority="balanced",
        expected_model="gpt-4o-mini",
        task_type="coding",
        complexity=1,
        confidence=0.97,
        reasoning="Trivial coding task, cheap model sufficient",
        needs_web=False,
        estimated_tokens=30
    ),
    RoutingExample(
        query="Design a database schema for an e-commerce platform with users, products, orders, and inventory",
        context="",
        user_priority="quality",
        expected_model="gpt-4o",
        task_type="coding",
        complexity=4,
        confidence=0.92,
        reasoning="Complex database design requires systematic thinking",
        needs_web=False,
        estimated_tokens=1500
    ),
    RoutingExample(
        query="Optimize this SQL query that's running slow: SELECT * FROM users WHERE.. .",
        context="",
        user_priority="balanced",
        expected_model="gpt-4o",
        task_type="coding",
        complexity=3,
        confidence=0.89,
        reasoning="Query optimization requires deep SQL knowledge",
        needs_web=False,
        estimated_tokens=400
    ),
    RoutingExample(
        query="Convert this JavaScript code to TypeScript with proper types",
        context="",
        user_priority="balanced",
        expected_model="kimi-k2",
        task_type="coding",
        complexity=3,
        confidence=0.88,
        reasoning="Type conversion task, Kimi handles well",
        needs_web=False,
        estimated_tokens=600
    ),
    RoutingExample(
        query="Implement a custom React hook for form validation",
        context="",
        user_priority="balanced",
        expected_model="gpt-4o",
        task_type="coding",
        complexity=3,
        confidence=0.90,
        reasoning="React patterns require good coding model",
        needs_web=False,
        estimated_tokens=400
    ),
    RoutingExample(
        query="Write unit tests for this payment processing function with edge cases",
        context="",
        user_priority="quality",
        expected_model="gpt-4o",
        task_type="coding",
        complexity=4,
        confidence=0.91,
        reasoning="Test writing needs thoroughness",
        needs_web=False,
        estimated_tokens=800
    ),
    RoutingExample(
        query="Explain what this regex does: ^(? =.*[A-Z])(?=.*[0-9]).{8,}$",
        context="",
        user_priority="balanced",
        expected_model="gpt-4o-mini",
        task_type="coding",
        complexity=2,
        confidence=0.88,
        reasoning="Regex explanation is straightforward",
        needs_web=False,
        estimated_tokens=150
    ),

    # =========================================================================
    # REASONING & MATH → gpt-4o or kimi-k2
    # =========================================================================

    RoutingExample(
        query="Prove that the square root of 2 is irrational",
        context="",
        user_priority="quality",
        expected_model="gpt-4o",
        task_type="math",
        complexity=4,
        confidence=0.93,
        reasoning="Mathematical proof requires rigorous reasoning",
        needs_web=False,
        estimated_tokens=500
    ),
    RoutingExample(
        query="If a train leaves Chicago at 9am going 60mph and another leaves NYC at 10am going 80mph, when do they meet?",
        context="",
        user_priority="balanced",
        expected_model="gpt-4o",
        task_type="reasoning",
        complexity=3,
        confidence=0.90,
        reasoning="Multi-step word problem requires careful reasoning",
        needs_web=False,
        estimated_tokens=300
    ),
    RoutingExample(
        query="Explain the P vs NP problem and its implications",
        context="",
        user_priority="quality",
        expected_model="gpt-4o",
        task_type="reasoning",
        complexity=5,
        confidence=0.94,
        reasoning="Complex theoretical CS requires deep understanding",
        needs_web=False,
        estimated_tokens=800
    ),
    RoutingExample(
        query="Analyze the logical fallacies in this argument:  [argument text]",
        context="",
        user_priority="balanced",
        expected_model="gpt-4o",
        task_type="reasoning",
        complexity=4,
        confidence=0.89,
        reasoning="Logical analysis requires strong reasoning",
        needs_web=False,
        estimated_tokens=400
    ),
    RoutingExample(
        query="Solve this system of equations:  2x + 3y = 10, 4x - y = 5",
        context="",
        user_priority="balanced",
        expected_model="kimi-k2",
        task_type="math",
        complexity=2,
        confidence=0.91,
        reasoning="Standard algebra problem",
        needs_web=False,
        estimated_tokens=200
    ),
    RoutingExample(
        query="Calculate the derivative of f(x) = x^3 * sin(x)",
        context="",
        user_priority="balanced",
        expected_model="gpt-4o",
        task_type="math",
        complexity=3,
        confidence=0.92,
        reasoning="Calculus problem with product rule",
        needs_web=False,
        estimated_tokens=250
    ),

    # =========================================================================
    # RESEARCH → perplexity-sonar-pro (ONLY with web)
    # =========================================================================

    RoutingExample(
        query="What are the latest developments in quantum computing in 2024?",
        context="",
        user_priority="balanced",
        expected_model="perplexity-sonar-pro",
        task_type="research",
        complexity=3,
        confidence=0.96,
        reasoning="Requires current information from the web",
        needs_web=True,
        estimated_tokens=500
    ),
    RoutingExample(
        query="Find recent research papers on transformer efficiency improvements",
        context="",
        user_priority="quality",
        expected_model="perplexity-sonar-pro",
        task_type="research",
        complexity=4,
        confidence=0.97,
        reasoning="Academic research needs web search and citations",
        needs_web=True,
        estimated_tokens=800
    ),
    RoutingExample(
        query="What's the current stock price of Apple?",
        context="",
        user_priority="speed",
        expected_model="perplexity-sonar-pro",
        task_type="research",
        complexity=1,
        confidence=0.98,
        reasoning="Real-time financial data requires web access",
        needs_web=True,
        estimated_tokens=100
    ),
    RoutingExample(
        query="Who won the latest Nobel Prize in Physics?",
        context="",
        user_priority="balanced",
        expected_model="perplexity-sonar-pro",
        task_type="research",
        complexity=2,
        confidence=0.95,
        reasoning="Recent event information needs web search",
        needs_web=True,
        estimated_tokens=200
    ),
    RoutingExample(
        query="Compare the specs of iPhone 16 vs Samsung Galaxy S24",
        context="",
        user_priority="balanced",
        expected_model="perplexity-sonar-pro",
        task_type="research",
        complexity=3,
        confidence=0.94,
        reasoning="Current product comparison needs up-to-date info",
        needs_web=True,
        estimated_tokens=600
    ),
    RoutingExample(
        query="What are the latest AI regulations in the EU?",
        context="",
        user_priority="balanced",
        expected_model="perplexity-sonar-pro",
        task_type="research",
        complexity=3,
        confidence=0.96,
        reasoning="Policy/regulatory info changes frequently",
        needs_web=True,
        estimated_tokens=500
    ),
    RoutingExample(
        query="What happened in the news today?",
        context="",
        user_priority="speed",
        expected_model="perplexity-sonar-pro",
        task_type="research",
        complexity=2,
        confidence=0.97,
        reasoning="Current events require real-time web access",
        needs_web=True,
        estimated_tokens=400
    ),

    # =========================================================================
    # LONG CONTEXT → gemini-2.5-flash
    # =========================================================================

    RoutingExample(
        query="Summarize this 100-page research paper:  [very long document]",
        context="",
        user_priority="balanced",
        expected_model="gemini-2.5-flash",
        task_type="long_context",
        complexity=3,
        confidence=0.95,
        reasoning="Very long document, needs 1M context window",
        needs_web=False,
        estimated_tokens=5000
    ),
    RoutingExample(
        query="Analyze this entire codebase and identify potential security issues:  [large codebase]",
        context="",
        user_priority="balanced",
        expected_model="gemini-2.5-flash",
        task_type="long_context",
        complexity=4,
        confidence=0.92,
        reasoning="Large codebase analysis needs massive context",
        needs_web=False,
        estimated_tokens=8000
    ),
    RoutingExample(
        query="Read through these meeting transcripts from the past month and summarize key decisions",
        context="",
        user_priority="balanced",
        expected_model="gemini-2.5-flash",
        task_type="summarization",
        complexity=3,
        confidence=0.93,
        reasoning="Multiple documents, gemini handles long context best",
        needs_web=False,
        estimated_tokens=3000
    ),
    RoutingExample(
        query="Compare these 5 legal contracts and highlight differences",
        context="",
        user_priority="balanced",
        expected_model="gemini-2.5-flash",
        task_type="long_context",
        complexity=4,
        confidence=0.91,
        reasoning="Multiple long documents require large context",
        needs_web=False,
        estimated_tokens=6000
    ),

    # =========================================================================
    # CREATIVE WRITING → gpt-4o (or claude when added)
    # =========================================================================

    RoutingExample(
        query="Write a compelling product description for wireless earbuds",
        context="",
        user_priority="quality",
        expected_model="gpt-4o",
        task_type="creative",
        complexity=3,
        confidence=0.90,
        reasoning="Marketing copy benefits from strong language model",
        needs_web=False,
        estimated_tokens=300
    ),
    RoutingExample(
        query="Help me write an emotional best man speech for my brother's wedding",
        context="",
        user_priority="quality",
        expected_model="gpt-4o",
        task_type="creative",
        complexity=4,
        confidence=0.92,
        reasoning="Emotional personal writing needs quality model",
        needs_web=False,
        estimated_tokens=600
    ),
    RoutingExample(
        query="Write a short horror story about a haunted lighthouse",
        context="",
        user_priority="balanced",
        expected_model="gpt-4o",
        task_type="creative",
        complexity=3,
        confidence=0.88,
        reasoning="Creative fiction writing",
        needs_web=False,
        estimated_tokens=800
    ),
    RoutingExample(
        query="Create detailed API documentation for this REST endpoint",
        context="",
        user_priority="quality",
        expected_model="gpt-4o",
        task_type="creative",
        complexity=3,
        confidence=0.89,
        reasoning="Technical writing with structure",
        needs_web=False,
        estimated_tokens=500
    ),
    RoutingExample(
        query="Write a professional email declining a job offer politely",
        context="",
        user_priority="balanced",
        expected_model="gpt-4o-mini",
        task_type="creative",
        complexity=2,
        confidence=0.85,
        reasoning="Simple professional email, cheaper model works",
        needs_web=False,
        estimated_tokens=200
    ),

    # =========================================================================
    # USER PRIORITY VARIATIONS
    # =========================================================================

    RoutingExample(
        query="Explain machine learning to a beginner",
        context="",
        user_priority="speed",
        expected_model="gemini-2.5-flash",
        task_type="simple_qa",
        complexity=2,
        confidence=0.88,
        reasoning="User prioritizes speed, gemini is fastest",
        needs_web=False,
        estimated_tokens=400
    ),
    RoutingExample(
        query="Explain machine learning to a beginner",
        context="",
        user_priority="cost",
        expected_model="gpt-4o-mini",
        task_type="simple_qa",
        complexity=2,
        confidence=0.87,
        reasoning="User prioritizes cost, use cheapest",
        needs_web=False,
        estimated_tokens=400
    ),
    RoutingExample(
        query="Explain machine learning to a beginner",
        context="",
        user_priority="quality",
        expected_model="gpt-4o",
        task_type="simple_qa",
        complexity=2,
        confidence=0.90,
        reasoning="User prioritizes quality, use best model",
        needs_web=False,
        estimated_tokens=400
    ),

    # =========================================================================
    # KIMI-K2 SPECIFIC EXAMPLES
    # =========================================================================

    RoutingExample(
        query="帮我写一段Python代码来处理中文文本",
        context="",
        user_priority="balanced",
        expected_model="kimi-k2",
        task_type="coding",
        complexity=2,
        confidence=0.93,
        reasoning="Chinese language query, Kimi excels at Chinese",
        needs_web=False,
        estimated_tokens=300
    ),
    RoutingExample(
        query="Analyze this complex mathematical proof step by step",
        context="",
        user_priority="quality",
        expected_model="kimi-k2",
        task_type="math",
        complexity=5,
        confidence=0.90,
        reasoning="Kimi has strong math reasoning capabilities",
        needs_web=False,
        estimated_tokens=1000
    ),
    RoutingExample(
        query="Review this code and suggest architectural improvements",
        context="[Previous discussion about system design]",
        user_priority="quality",
        expected_model="kimi-k2",
        task_type="coding",
        complexity=4,
        confidence=0.88,
        reasoning="Code review with architectural focus",
        needs_web=False,
        estimated_tokens=800
    ),
]


# =============================================================================
# DATA AUGMENTATION
# =============================================================================

def augment_example(example: RoutingExample) -> List[RoutingExample]:
    """Generate variations of a training example."""
    variations = []
    query = example.query

    # Variation templates
    templates = [
        f"Can you {query. lower().rstrip('? .')}?",
        f"I need help with:  {query}",
        f"Please {query.lower().rstrip('?.')}",
        f"{query} Thanks!",
        f"Hey, {query. lower()}",
    ]

    for template in templates:
        var = RoutingExample(
            query=template,
            context=example.context,
            user_priority=example.user_priority,
            expected_model=example.expected_model,
            task_type=example. task_type,
            complexity=example. complexity,
            confidence=example.confidence - 0.02,  # Slightly lower confidence for variations
            reasoning=example.reasoning,
            needs_web=example.needs_web,
            estimated_tokens=example.estimated_tokens
        )
        variations.append(var)

    return variations


def generate_training_dataset(
    include_augmentation: bool = True,
    shuffle: bool = True
) -> List[Dict[str, Any]]:
    """Generate the complete training dataset."""
    from ..config import generate_router_system_prompt

    system_prompt = generate_router_system_prompt()
    dataset = []

    for example in TRAINING_EXAMPLES:
        # Add original example
        dataset.append(example.to_training_format(system_prompt))

        # Add augmented variations
        if include_augmentation:
            for variation in augment_example(example):
                dataset.append(variation.to_training_format(system_prompt))

    if shuffle:
        random.shuffle(dataset)

    return dataset


def save_training_data(filepath: str = "router_training_data. jsonl"):
    """Save training data to JSONL file for OpenAI fine-tuning."""
    dataset = generate_training_dataset()

    with open(filepath, 'w') as f:
        for item in dataset:
            f.write(json.dumps(item) + '\n')

    print(f"Saved {len(dataset)} training examples to {filepath}")
    return filepath
