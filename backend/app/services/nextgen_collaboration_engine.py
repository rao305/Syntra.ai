"""
Next-Generation Collaboration Engine

Integrates all phases of the DAC Intelligence Orchestrator:
- Intent Classification & Dynamic Routing
- Adaptive Model Swarming  
- Memory Lattice & Truth Arbitration
- Task Graph Building & Orchestration

This replaces the static sequential collaboration with intelligent swarming behavior.
"""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import asyncio
import time
import json
from app.services.intent_classifier import intent_classifier, IntentVector
from app.services.adaptive_model_swarm import AdaptiveModelSwarm, SwarmResult
from app.services.memory_lattice import MemoryLattice, Insight, InsightType
from app.services.truth_arbitrator import TruthArbitrator
from app.services.task_orchestrator import task_orchestrator, WorkflowDAG
from app.models.provider_key import ProviderType

import logging
logger = logging.getLogger(__name__)

class CollaborationMode(Enum):
    """Next-gen collaboration modes"""
    INTELLIGENT_SWARM = "intelligent_swarm"    # Full AI orchestration (default)
    TASK_WORKFLOW = "task_workflow"            # DAG-based task orchestration  
    PARALLEL_MODELS = "parallel_models"        # Simple parallel execution
    LEGACY_SEQUENTIAL = "legacy_sequential"    # Original 5-agent pipeline

@dataclass
class NextGenCollaborationResult:
    """Comprehensive result from next-gen collaboration"""
    final_output: str
    collaboration_mode: CollaborationMode
    
    # Intelligence orchestration results
    intent_analysis: Optional[IntentVector] = None
    swarm_result: Optional[SwarmResult] = None
    workflow_result: Optional[Dict[str, Any]] = None
    
    # Memory and truth systems
    memory_updates: List[Insight] = None
    conflicts_resolved: int = 0
    
    # Performance metrics
    total_time_ms: float = 0
    model_utilization: Dict[str, float] = None
    parallelization_efficiency: float = 0.0
    
    # Transparency data for UI
    model_executions: List[Dict[str, Any]] = None
    active_contradictions: List[Dict[str, Any]] = None
    convergence_score: float = 0.0
    insights_generated: int = 0

class NextGenCollaborationEngine:
    """
    The complete DAC Intelligence Orchestrator that transforms multi-model
    collaboration from static sequential agents into dynamic intelligent swarming.
    """
    
    def __init__(self):
        # Initialize all subsystems
        self.memory_lattice = MemoryLattice()
        self.truth_arbitrator = TruthArbitrator()
        self.model_swarm = AdaptiveModelSwarm(self.memory_lattice, self.truth_arbitrator)
        
        # Performance tracking
        self.collaboration_history = []
        self.performance_metrics = {
            "total_collaborations": 0,
            "avg_execution_time": 0.0,
            "success_rate": 0.0,
            "avg_convergence": 0.0
        }
    
    async def collaborate(
        self,
        user_query: str,
        turn_id: str,
        api_keys: Dict[str, str],
        collaboration_mode: CollaborationMode = CollaborationMode.INTELLIGENT_SWARM,
        context: Optional[str] = None,
        max_parallel_models: int = 5,
        enable_memory_lattice: bool = True,
        enable_truth_arbitration: bool = True
    ) -> NextGenCollaborationResult:
        """
        Execute next-generation collaboration with full intelligence orchestration.
        
        This is the main entry point that replaces the old collaboration_engine.py
        """
        start_time = time.perf_counter()
        
        try:
            # Phase 1: Intent Classification & Analysis
            logger.info("🧠 Phase 1: Analyzing intent for query: {user_query[:100]}...")
            intent_vector = await intent_classifier.classify_intent(user_query, context)
            
            logger.info("📊 Intent analysis complete. Detected needs: {dict(intent_vector.needs)}")
            logger.info("🎯 Complexity: {intent_vector.complexity:.2f}, Urgency: {intent_vector.urgency:.2f}")
            
            # Phase 2: Choose execution strategy
            execution_mode = self._choose_execution_strategy(
                collaboration_mode, intent_vector, len(api_keys)
            )
            
            logger.info("⚡ Selected execution mode: {execution_mode.value}")
            
            # Phase 3: Execute based on chosen strategy
            if execution_mode == CollaborationMode.INTELLIGENT_SWARM:
                result = await self._execute_intelligent_swarm(
                    user_query, intent_vector, turn_id, api_keys, context,
                    max_parallel_models, enable_memory_lattice, enable_truth_arbitration
                )
            elif execution_mode == CollaborationMode.TASK_WORKFLOW:
                result = await self._execute_task_workflow(
                    user_query, intent_vector, turn_id, api_keys, context
                )
            elif execution_mode == CollaborationMode.PARALLEL_MODELS:
                result = await self._execute_parallel_models(
                    user_query, intent_vector, turn_id, api_keys, context
                )
            else:  # LEGACY_SEQUENTIAL
                result = await self._execute_legacy_sequential(
                    user_query, turn_id, api_keys, context
                )
            
            # Phase 4: Finalize and track performance
            total_time = (time.perf_counter() - start_time) * 1000
            result.total_time_ms = total_time
            result.collaboration_mode = execution_mode
            result.intent_analysis = intent_vector
            
            # Update performance tracking
            self._update_performance_metrics(result)
            
            logger.info("✅ Collaboration complete in {total_time:.0f}ms")
            logger.info("🎯 Convergence: {result.convergence_score:.2%}, Insights: {result.insights_generated}")
            
            return result
            
        except Exception as e:
            logger.error("❌ Collaboration failed: {str(e)}")
            # Graceful degradation
            return await self._fallback_collaboration(user_query, turn_id, api_keys, str(e))
    
    def _choose_execution_strategy(
        self, 
        requested_mode: CollaborationMode,
        intent_vector: IntentVector,
        num_available_models: int
    ) -> CollaborationMode:
        """Intelligently choose the best execution strategy"""
        
        # If user explicitly requested a mode, honor it
        if requested_mode != CollaborationMode.INTELLIGENT_SWARM:
            return requested_mode
        
        # Intelligent mode selection based on query characteristics
        complexity = intent_vector.complexity
        active_intents = sum(1 for confidence in intent_vector.needs.values() if confidence > 0.3)
        
        # High complexity + multiple intents = workflow orchestration
        if complexity > 0.7 and active_intents >= 3:
            return CollaborationMode.TASK_WORKFLOW
        
        # Medium complexity + multiple models = intelligent swarm
        elif complexity > 0.4 and num_available_models >= 3:
            return CollaborationMode.INTELLIGENT_SWARM
        
        # Simple queries + multiple models = parallel execution
        elif num_available_models >= 2:
            return CollaborationMode.PARALLEL_MODELS
        
        # Fallback to sequential for single model or simple cases
        else:
            return CollaborationMode.LEGACY_SEQUENTIAL
    
    async def _execute_intelligent_swarm(
        self,
        user_query: str,
        intent_vector: IntentVector,
        turn_id: str,
        api_keys: Dict[str, str],
        context: Optional[str],
        max_parallel: int,
        enable_memory: bool,
        enable_truth: bool
    ) -> NextGenCollaborationResult:
        """Execute full intelligent swarm with all advanced features"""
        
        logger.info("🚀 Executing Intelligent Swarm mode...")
        
        # Execute adaptive model swarm
        swarm_result = await self.model_swarm.execute_swarm(
            user_query=user_query,
            intent_vector=intent_vector,
            api_keys=api_keys,
            max_parallel=max_parallel,
            timeout_seconds=30
        )
        
        # Prepare UI transparency data
        model_executions = []
        for execution in swarm_result.all_executions:
            model_executions.append({
                "model": execution.agent.model_id,
                "role": execution.agent.role.value,
                "status": "completed" if not execution.error else "error",
                "progress": 100 if not execution.error else 0,
                "keyInsight": execution.key_insights[0] if execution.key_insights else "No insights",
                "confidence": execution.confidence_score,
                "contradictions": len(execution.contradictions),
                "citations": len(execution.citations),
                "executionTime": execution.execution_time_ms,
                "tokensUsed": execution.metadata.get("response_length", 0)
            })
        
        # Prepare conflict data for UI
        active_contradictions = []
        for resolution in swarm_result.conflict_resolutions:
            active_contradictions.append({
                "id": resolution.conflict_id,
                "type": resolution.conflict_type.value,
                "severity": 0.7,  # Placeholder
                "status": "resolved" if resolution.final_verdict else "unresolved",
                "resolution": resolution.final_verdict,
                "confidence": resolution.confidence_score
            })
        
        return NextGenCollaborationResult(
            final_output=swarm_result.final_output,
            collaboration_mode=CollaborationMode.INTELLIGENT_SWARM,
            intent_analysis=intent_vector,
            swarm_result=swarm_result,
            memory_updates=swarm_result.memory_updates,
            conflicts_resolved=len(swarm_result.conflict_resolutions),
            total_time_ms=swarm_result.total_time_ms,
            model_utilization={
                execution.agent.model_id: execution.confidence_score 
                for execution in swarm_result.all_executions
            },
            parallelization_efficiency=swarm_result.performance_metrics.get("parallelization_efficiency", 0.0),
            model_executions=model_executions,
            active_contradictions=active_contradictions,
            convergence_score=swarm_result.convergence_score,
            insights_generated=len(swarm_result.memory_updates)
        )
    
    async def _execute_task_workflow(
        self,
        user_query: str,
        intent_vector: IntentVector,
        turn_id: str,
        api_keys: Dict[str, str],
        context: Optional[str]
    ) -> NextGenCollaborationResult:
        """Execute DAG-based task workflow orchestration"""
        
        logger.info("📋 Executing Task Workflow mode...")
        
        # Build workflow DAG
        available_models = list(api_keys.keys())
        workflow = await task_orchestrator.build_workflow_dag(
            user_query, intent_vector, available_models
        )
        
        logger.info("📊 Built workflow with {len(workflow.nodes)} tasks, {workflow.parallelization_opportunities} parallel opportunities")
        
        # Execute workflow
        workflow_result = await task_orchestrator.execute_workflow(
            workflow, user_query, api_keys, context or ""
        )
        
        # Convert workflow data for UI
        model_executions = []
        for node in workflow.nodes.values():
            if node.status.value in ["completed", "running"]:
                model_executions.append({
                    "model": node.assigned_model or "unknown",
                    "role": node.task_type.value,
                    "status": node.status.value,
                    "progress": 100 if node.status.value == "completed" else 50,
                    "keyInsight": node.result[:100] + "..." if node.result else node.description,
                    "confidence": node.confidence,
                    "contradictions": 0,
                    "citations": 0,
                    "executionTime": node.execution_time_ms or 0,
                    "tokensUsed": len(node.result or "") 
                })
        
        return NextGenCollaborationResult(
            final_output=workflow_result["final_result"],
            collaboration_mode=CollaborationMode.TASK_WORKFLOW,
            intent_analysis=intent_vector,
            workflow_result=workflow_result,
            total_time_ms=workflow_result["execution_time_ms"],
            model_utilization={
                node.assigned_model: node.confidence 
                for node in workflow.nodes.values() 
                if node.assigned_model and node.status.value == "completed"
            },
            model_executions=model_executions,
            active_contradictions=[],
            convergence_score=0.8,  # Workflow naturally converges
            insights_generated=workflow_result["tasks_completed"]
        )
    
    async def _execute_parallel_models(
        self,
        user_query: str,
        intent_vector: IntentVector,
        turn_id: str,
        api_keys: Dict[str, str],
        context: Optional[str]
    ) -> NextGenCollaborationResult:
        """Execute simple parallel model execution without full orchestration"""
        
        logger.info("⚡ Executing Parallel Models mode...")

        # Route to best models for this intent
        available_models = list(api_keys.keys())
        model_assignments = intent_classifier.route_to_models(
            intent_vector, available_models, max_models=3
        )

        # Fallback: if no models assigned, use all 4 available models
        if not model_assignments:
            logger.warning("⚠️  No models assigned by intent classifier, using all 4 available models as fallback")
            # Map provider names to model names (all 4 providers: OpenAI, Gemini, Kimi, Perplexity)
            provider_to_model = {
                "openai": "gpt-4o-mini",
                "gemini": "gemini-2.0-flash-exp",
                "perplexity": "sonar",
                "kimi": "moonshot-v1-8k"
            }
            model_assignments = [
                (provider_to_model.get(provider, provider), 1.0, [])
                for provider in available_models
                if provider in provider_to_model
            ]  # Use all 4 models
            logger.info("📌 Using all 4 fallback models: {[m[0] for m in model_assignments]}")

        # Execute models in parallel
        tasks = []
        for model_id, score, assigned_intents in model_assignments:
            task = self._execute_simple_model(
                model_id, user_query, api_keys, context or ""
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Simple synthesis - use highest scoring result
        best_result = ""
        best_score = 0.0
        
        model_executions = []
        for i, (model_assignment, result) in enumerate(zip(model_assignments, results)):
            model_id, score, intents = model_assignment
            
            if isinstance(result, Exception):
                model_executions.append({
                    "model": model_id,
                    "role": "parallel_executor",
                    "status": "error",
                    "progress": 0,
                    "keyInsight": f"Error: {str(result)}",
                    "confidence": 0.0,
                    "contradictions": 0,
                    "citations": 0,
                    "executionTime": 0,
                    "tokensUsed": 0
                })
            else:
                content = result.get("content", "")
                confidence = result.get("confidence", score / 10)  # Convert 0-10 to 0-1
                
                model_executions.append({
                    "model": model_id,
                    "role": "parallel_executor", 
                    "status": "completed",
                    "progress": 100,
                    "keyInsight": content[:100] + "..." if len(content) > 100 else content,
                    "confidence": confidence,
                    "contradictions": 0,
                    "citations": 0,
                    "executionTime": result.get("execution_time_ms", 1000),
                    "tokensUsed": len(content)
                })
                
                if confidence > best_score:
                    best_score = confidence
                    best_result = content
        
        return NextGenCollaborationResult(
            final_output=best_result or "No successful model executions",
            collaboration_mode=CollaborationMode.PARALLEL_MODELS,
            intent_analysis=intent_vector,
            model_utilization={
                assignment[0]: assignment[1] / 10 
                for assignment in model_assignments
            },
            model_executions=model_executions,
            active_contradictions=[],
            convergence_score=0.6,  # Medium convergence for parallel
            insights_generated=len([r for r in results if not isinstance(r, Exception)])
        )
    
    async def _execute_legacy_sequential(
        self,
        user_query: str,
        turn_id: str,
        api_keys: Dict[str, str],
        context: Optional[str]
    ) -> NextGenCollaborationResult:
        """Fallback to original sequential collaboration for compatibility"""
        
        logger.info("🔄 Executing Legacy Sequential mode...")
        
        # Import and use original collaboration engine
        from app.services.collaboration_engine import CollaborationEngine
        
        legacy_engine = CollaborationEngine()
        legacy_result = await legacy_engine.collaborate(
            user_query, turn_id, api_keys, collaboration_mode=True
        )
        
        # Convert legacy result to new format
        model_executions = []
        for agent_output in legacy_result.agent_outputs:
            model_executions.append({
                "model": agent_output.provider,
                "role": agent_output.role.value,
                "status": "completed",
                "progress": 100,
                "keyInsight": agent_output.content[:100] + "...",
                "confidence": 0.8,  # Default confidence
                "contradictions": 0,
                "citations": 0,
                "executionTime": legacy_result.total_time_ms / len(legacy_result.agent_outputs),
                "tokensUsed": len(agent_output.content)
            })
        
        return NextGenCollaborationResult(
            final_output=legacy_result.final_report,
            collaboration_mode=CollaborationMode.LEGACY_SEQUENTIAL,
            total_time_ms=legacy_result.total_time_ms,
            model_executions=model_executions,
            active_contradictions=[],
            convergence_score=0.7,  # Reasonable for sequential
            insights_generated=len(legacy_result.agent_outputs)
        )
    
    async def _execute_simple_model(
        self,
        model_id: str,
        user_query: str,
        api_keys: Dict[str, str],
        context: str
    ) -> Dict[str, Any]:
        """Execute a single model with simple prompting"""
        
        start_time = time.perf_counter()
        
        # Get provider and API key
        provider = self._get_provider_for_model(model_id)
        api_key = api_keys.get(provider)
        
        if not api_key:
            raise ValueError(f"No API key for provider {provider}")
        
        # Build simple prompt
        prompt = f"User Query: {user_query}"
        if context:
            prompt = f"Context: {context}\n\n{prompt}"
        
        # Execute based on provider
        try:
            if provider == "openai":
                from app.adapters.openai_adapter import call_openai
                response = await call_openai(
                    messages=[{"role": "user", "content": prompt}],
                    model=model_id,
                    api_key=api_key,
                    temperature=0.7
                )
                content = response.content

            elif provider == "gemini":
                from app.adapters.gemini import call_gemini
                response = await call_gemini(
                    messages=[{"role": "user", "content": prompt}],
                    model=model_id,
                    api_key=api_key,
                    temperature=0.7
                )
                content = response.content

            elif provider == "perplexity":
                from app.adapters.perplexity import call_perplexity
                response = await call_perplexity(
                    messages=[{"role": "user", "content": prompt}],
                    model=model_id,
                    api_key=api_key
                )
                content = response.content

            elif provider == "kimi":
                from app.adapters.kimi import call_kimi
                response = await call_kimi(
                    messages=[{"role": "user", "content": prompt}],
                    model=model_id,
                    api_key=api_key,
                    temperature=0.7
                )
                content = response.content

            else:
                raise ValueError(f"Unsupported provider: {provider}")
            
            execution_time = (time.perf_counter() - start_time) * 1000
            
            return {
                "content": content,
                "confidence": 0.7,  # Default confidence
                "execution_time_ms": execution_time,
                "model": model_id,
                "provider": provider
            }
            
        except Exception as e:
            raise e
    
    def _get_provider_for_model(self, model_id: str) -> str:
        """Map model IDs to provider names (matching ProviderType values)"""
        provider_map = {
            # OpenAI models
            "gpt-4o": "openai",
            "gpt-4o-mini": "openai",
            "gpt-4-turbo": "openai",
            "gpt-3.5-turbo": "openai",

            # Gemini models (use "gemini" to match ProviderType.GEMINI)
            "gemini-2.0-flash": "gemini",
            "gemini-2.0-flash-exp": "gemini",
            "gemini-1.5-pro": "gemini",
            "gemini-1.5-flash": "gemini",
            "gemini-pro": "gemini",

            # Perplexity models
            "sonar": "perplexity",
            "sonar-pro": "perplexity",

            # Kimi models (use "kimi" to match ProviderType.KIMI)
            "kimi": "kimi",
            "moonshot-v1-8k": "kimi",
            "moonshot-v1-32k": "kimi",
            "moonshot-v1-128k": "kimi",
        }
        return provider_map.get(model_id, "openai")
    
    async def _fallback_collaboration(
        self,
        user_query: str,
        turn_id: str,
        api_keys: Dict[str, str],
        error: str
    ) -> NextGenCollaborationResult:
        """Fallback when all collaboration modes fail"""
        
        # Try simple single model execution
        if "openai" in api_keys:
            try:
                result = await self._execute_simple_model(
                    "gpt-4o", user_query, api_keys, ""
                )
                
                return NextGenCollaborationResult(
                    final_output=result["content"],
                    collaboration_mode=CollaborationMode.LEGACY_SEQUENTIAL,
                    model_executions=[{
                        "model": "gpt-4o",
                        "role": "fallback", 
                        "status": "completed",
                        "progress": 100,
                        "keyInsight": "Fallback execution",
                        "confidence": 0.5,
                        "contradictions": 0,
                        "citations": 0,
                        "executionTime": result["execution_time_ms"],
                        "tokensUsed": len(result["content"])
                    }],
                    active_contradictions=[],
                    convergence_score=1.0,  # Single model = perfect convergence
                    insights_generated=1
                )
            except Exception as fallback_error:
                logger.warning(f"Failed to create fallback result: {fallback_error}")
                pass
        
        # Ultimate fallback
        return NextGenCollaborationResult(
            final_output=f"I apologize, but I encountered technical difficulties: {error}. Please try your request again.",
            collaboration_mode=CollaborationMode.LEGACY_SEQUENTIAL,
            model_executions=[],
            active_contradictions=[],
            convergence_score=0.0,
            insights_generated=0
        )
    
    def _update_performance_metrics(self, result: NextGenCollaborationResult):
        """Update internal performance tracking"""
        
        self.collaboration_history.append(result)
        
        # Keep only last 100 collaborations
        if len(self.collaboration_history) > 100:
            self.collaboration_history = self.collaboration_history[-50:]
        
        # Update metrics
        total = len(self.collaboration_history)
        if total > 0:
            self.performance_metrics.update({
                "total_collaborations": total,
                "avg_execution_time": sum(r.total_time_ms for r in self.collaboration_history) / total,
                "success_rate": sum(1 for r in self.collaboration_history if r.final_output and not "difficulties" in r.final_output) / total,
                "avg_convergence": sum(r.convergence_score for r in self.collaboration_history) / total
            })
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        
        if not self.collaboration_history:
            return {"total_collaborations": 0}
        
        recent_results = self.collaboration_history[-20:]  # Last 20
        
        mode_distribution = {}
        for result in recent_results:
            mode = result.collaboration_mode.value
            mode_distribution[mode] = mode_distribution.get(mode, 0) + 1
        
        return {
            **self.performance_metrics,
            "recent_mode_distribution": mode_distribution,
            "memory_lattice_stats": self.memory_lattice.get_memory_statistics(),
            "truth_arbitration_stats": self.truth_arbitrator.get_arbitration_stats(),
            "recent_avg_insights": sum(r.insights_generated for r in recent_results) / len(recent_results),
            "recent_avg_convergence": sum(r.convergence_score for r in recent_results) / len(recent_results)
        }

# Global next-gen collaboration engine instance
nextgen_collaboration_engine = NextGenCollaborationEngine()