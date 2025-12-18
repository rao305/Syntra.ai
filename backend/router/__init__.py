"""
Syntra AI Intelligent Router - Phase 1 Complete Implementation

This module provides an intelligent, extensible query routing system that uses
a fine-tuned GPT-4o-mini model to route user queries to the optimal AI model.

Features:
- Fine-tuned routing model for intelligent decisions
- Extensible model registry pattern
- Cost, latency, and quality optimization
- Comprehensive training data and evaluation
- REST API endpoints for integration
"""

from .config import MODEL_REGISTRY, ROUTER_CONFIG, generate_router_system_prompt
from .intelligent_router import IntelligentRouter
from .metrics import RouterMetrics
from .cost_optimizer import CostOptimizer, CostAwareRouter, cost_optimizer

__all__ = [
    "MODEL_REGISTRY",
    "ROUTER_CONFIG",
    "generate_router_system_prompt",
    "IntelligentRouter",
    "RouterMetrics",
    "CostOptimizer",
    "CostAwareRouter",
    "cost_optimizer",
]
