"""
Adaptive Model Swarming (AMS) - Phase 2 Implementation

Real-time parallel model execution with dynamic arbitration and convergence.
This replaces static sequential agents with intelligent swarming behavior.
"""

from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import time
import json
import hashlib
from concurrent.futures import as_completed
from app.services.intent_classifier import IntentType, IntentVector, intent_classifier
from app.services.memory_lattice import MemoryLattice, Insight, Contradiction
from app.services.truth_arbitrator import TruthArbitrator, ConflictResolution
from app.adapters.openai_adapter import call_openai
from app.adapters.gemini import call_gemini
from app.adapters.perplexity import call_perplexity

class SwarmRole(Enum):
    """Dynamic roles assigned based on intent and model capabilities"""
    LEAD_RESEARCHER = "lead_researcher"      # Primary research and fact-finding
    SPECIALIST = "specialist"                # Domain-specific expertise
    CRITIC = "critic"                       # Quality control and validation
    SYNTHESIZER = "synthesizer"             # Integration and final output
    VERIFIER = "verifier"                   # Fact-checking and accuracy
    CREATIVE = "creative"                   # Innovation and generation
    DEBUGGER = "debugger"                   # Problem-solving and fixes

@dataclass
class SwarmAgent:
    """Individual agent in the model swarm"""
    model_id: str
    provider: str
    role: SwarmRole
    assigned_intents: List[IntentType]
    confidence_threshold: float
    execution_priority: int  # 1 = highest priority
    specialized_prompt: str = ""

@dataclass 
class SwarmExecution:
    """Results from a single agent execution"""
    agent: SwarmAgent
    content: str
    execution_time_ms: float
    confidence_score: float
    citations: List[str] = field(default_factory=list)
    key_insights: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SwarmResult:
    """Final result from adaptive model swarming"""
    final_output: str
    all_executions: List[SwarmExecution]
    convergence_score: float  # How well models agreed (0-1)
    total_time_ms: float
    swarm_composition: List[SwarmAgent]
    conflict_resolutions: List[ConflictResolution]
    performance_metrics: Dict[str, float]
    memory_updates: List[Insight]

class AdaptiveModelSwarm:
    """Orchestrates parallel model execution with dynamic arbitration"""
    
    def __init__(self, memory_lattice: MemoryLattice, truth_arbitrator: TruthArbitrator):
        self.memory = memory_lattice
        self.arbitrator = truth_arbitrator
        self.active_swarms = {}  # Track running swarms
        
    async def execute_swarm(
        self,
        user_query: str,
        intent_vector: IntentVector,
        api_keys: Dict[str, str],
        max_parallel: int = 5,
        timeout_seconds: int = 30,
        convergence_threshold: float = 0.8
    ) -> SwarmResult:
        """
        Execute adaptive model swarm with parallel processing and real-time arbitration.
        """
        start_time = time.perf_counter()
        swarm_id = self._generate_swarm_id(user_query)
        
        try:
            # 1. Build optimal swarm composition
            swarm_agents = self._compose_swarm(intent_vector, api_keys, max_parallel)
            
            # 2. Get relevant context from memory lattice
            context = await self.memory.get_relevant_context(user_query, intent_vector)
            
            # 3. Execute models in parallel
            executions = await self._execute_parallel_models(
                swarm_agents, user_query, context, api_keys, timeout_seconds
            )
            
            # 4. Real-time arbitration and conflict resolution
            conflict_resolutions = await self._resolve_conflicts(executions, user_query)
            
            # 5. Convergence analysis
            convergence_score = self._calculate_convergence(executions)
            
            # 6. Synthesize final output
            final_output = await self._synthesize_outputs(
                executions, conflict_resolutions, user_query, api_keys
            )
            
            # 7. Update memory lattice
            memory_updates = await self._update_memory(executions, final_output, user_query)
            
            total_time = (time.perf_counter() - start_time) * 1000
            
            return SwarmResult(
                final_output=final_output,
                all_executions=executions,
                convergence_score=convergence_score,
                total_time_ms=total_time,
                swarm_composition=swarm_agents,
                conflict_resolutions=conflict_resolutions,
                performance_metrics=self._calculate_performance_metrics(executions, total_time),
                memory_updates=memory_updates
            )
            
        except Exception as e:
            # Graceful degradation
            return await self._fallback_execution(user_query, api_keys, str(e))
        finally:
            if swarm_id in self.active_swarms:
                del self.active_swarms[swarm_id]
    
    def _compose_swarm(
        self, 
        intent_vector: IntentVector, 
        api_keys: Dict[str, str],
        max_models: int
    ) -> List[SwarmAgent]:
        """Intelligently compose swarm based on intent vector and available models"""
        
        available_models = list(api_keys.keys())
        model_assignments = intent_classifier.route_to_models(
            intent_vector, available_models, max_models
        )
        
        swarm_agents = []
        role_assignment_priority = {
            IntentType.RESEARCH: SwarmRole.LEAD_RESEARCHER,
            IntentType.CRITIQUE: SwarmRole.CRITIC,
            IntentType.VERIFY: SwarmRole.VERIFIER,
            IntentType.GENERATE: SwarmRole.CREATIVE,
            IntentType.DEBUG: SwarmRole.DEBUGGER,
            IntentType.ANALYZE: SwarmRole.SPECIALIST,
            IntentType.SYNTHESIZE: SwarmRole.SYNTHESIZER
        }
        
        for i, (model_id, score, assigned_intents) in enumerate(model_assignments):
            # Assign primary role based on strongest intent
            primary_role = SwarmRole.SPECIALIST  # Default
            if assigned_intents:
                for intent in assigned_intents:
                    if intent in role_assignment_priority:
                        primary_role = role_assignment_priority[intent]
                        break
            
            agent = SwarmAgent(
                model_id=model_id,
                provider=self._get_provider_for_model(model_id),
                role=primary_role,
                assigned_intents=assigned_intents,
                confidence_threshold=0.7,
                execution_priority=i + 1,
                specialized_prompt=self._generate_specialized_prompt(primary_role, assigned_intents)
            )
            
            swarm_agents.append(agent)
        
        return swarm_agents
    
    async def _execute_parallel_models(
        self,
        agents: List[SwarmAgent],
        user_query: str,
        context: str,
        api_keys: Dict[str, str],
        timeout: int
    ) -> List[SwarmExecution]:
        """Execute all agents in parallel with timeout handling"""
        
        tasks = []
        for agent in agents:
            task = asyncio.create_task(
                self._execute_single_agent(agent, user_query, context, api_keys)
            )
            tasks.append(task)
        
        executions = []
        try:
            # Wait for all tasks with timeout
            completed = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout
            )
            
            for i, result in enumerate(completed):
                if isinstance(result, Exception):
                    # Create error execution
                    executions.append(SwarmExecution(
                        agent=agents[i],
                        content="",
                        execution_time_ms=0,
                        confidence_score=0.0,
                        error=str(result)
                    ))
                else:
                    executions.append(result)
                    
        except asyncio.TimeoutError:
            # Handle partial results
            for i, task in enumerate(tasks):
                if task.done() and not task.exception():
                    executions.append(task.result())
                else:
                    executions.append(SwarmExecution(
                        agent=agents[i],
                        content="",
                        execution_time_ms=0,
                        confidence_score=0.0,
                        error="Timeout"
                    ))
        
        return executions
    
    async def _execute_single_agent(
        self,
        agent: SwarmAgent,
        user_query: str,
        context: str,
        api_keys: Dict[str, str]
    ) -> SwarmExecution:
        """Execute a single agent with specialized prompting"""
        start_time = time.perf_counter()
        
        try:
            # Build specialized prompt
            full_prompt = self._build_agent_prompt(agent, user_query, context)
            
            messages = [
                {"role": "system", "content": agent.specialized_prompt},
                {"role": "user", "content": full_prompt}
            ]
            
            api_key = api_keys.get(agent.provider)
            if not api_key:
                raise ValueError(f"No API key for provider {agent.provider}")
            
            # Route to appropriate adapter
            if agent.provider == "openai":
                response = await call_openai(
                    messages=messages,
                    model=agent.model_id,
                    api_key=api_key,
                    temperature=0.7
                )
                content = response.content
                
            elif agent.provider == "google":
                response = await call_gemini(
                    messages=messages,
                    model=agent.model_id,
                    api_key=api_key,
                    temperature=0.7
                )
                content = response.content
                
            elif agent.provider == "perplexity":
                response = await call_perplexity(
                    messages=[{"role": "user", "content": full_prompt}],
                    model=agent.model_id,
                    api_key=api_key
                )
                content = response.content
                
            else:
                raise ValueError(f"Unsupported provider: {agent.provider}")
            
            # Extract insights and metadata
            insights, contradictions, citations = self._extract_insights(content, agent)
            confidence = self._calculate_confidence(content, agent)
            
            execution_time = (time.perf_counter() - start_time) * 1000
            
            return SwarmExecution(
                agent=agent,
                content=content,
                execution_time_ms=execution_time,
                confidence_score=confidence,
                citations=citations,
                key_insights=insights,
                contradictions=contradictions,
                metadata={
                    "prompt_length": len(full_prompt),
                    "response_length": len(content),
                    "intents_addressed": len(agent.assigned_intents)
                }
            )
            
        except Exception as e:
            execution_time = (time.perf_counter() - start_time) * 1000
            return SwarmExecution(
                agent=agent,
                content="",
                execution_time_ms=execution_time,
                confidence_score=0.0,
                error=str(e)
            )
    
    def _generate_specialized_prompt(self, role: SwarmRole, intents: List[IntentType]) -> str:
        """Generate role-specific system prompts"""
        
        base_prompts = {
            SwarmRole.LEAD_RESEARCHER: """You are the **Lead Researcher** in an AI model swarm. Your role is to find and verify current information with citations.

Focus on:
- Finding up-to-date, credible sources
- Providing proper citations with URLs and dates  
- Identifying key facts and data points
- Noting any information gaps or uncertainties

Always structure your response with clear citations and confidence levels.""",

            SwarmRole.SPECIALIST: """You are a **Domain Specialist** in an AI model swarm. Your role is to provide deep expertise in your assigned areas.

Focus on:
- Technical accuracy and depth
- Industry best practices and standards
- Detailed implementation guidance
- Potential risks and considerations

Provide authoritative, detailed analysis within your specialization.""",

            SwarmRole.CRITIC: """You are the **Quality Critic** in an AI model swarm. Your role is to find flaws, risks, and improvement opportunities.

Focus on:
- Identifying potential problems and edge cases
- Security vulnerabilities and risks
- Scalability and performance concerns
- Missing requirements or considerations

Be constructive but thorough in identifying issues.""",

            SwarmRole.SYNTHESIZER: """You are the **Synthesizer** in an AI model swarm. Your role is to integrate multiple perspectives into coherent solutions.

Focus on:
- Combining insights from multiple sources
- Resolving contradictions and conflicts
- Creating unified, actionable recommendations
- Ensuring completeness and coherence

Create well-structured, comprehensive responses.""",

            SwarmRole.VERIFIER: """You are the **Verifier** in an AI model swarm. Your role is fact-checking and accuracy validation.

Focus on:
- Checking claims against known facts
- Identifying potential inaccuracies or hallucinations
- Validating logical consistency
- Confirming technical details

Provide confidence scores and flag any uncertainties.""",

            SwarmRole.CREATIVE: """You are the **Creative Generator** in an AI model swarm. Your role is innovative solution generation.

Focus on:
- Generating novel approaches and ideas
- Creative problem-solving strategies
- Thinking outside conventional solutions
- Proposing innovative implementations

Balance creativity with feasibility and practicality.""",

            SwarmRole.DEBUGGER: """You are the **Problem Debugger** in an AI model swarm. Your role is systematic problem resolution.

Focus on:
- Root cause analysis and troubleshooting
- Step-by-step debugging approaches
- Systematic testing and validation methods
- Clear problem-solution mapping

Provide methodical, logical problem-solving approaches."""
        }
        
        prompt = base_prompts.get(role, base_prompts[SwarmRole.SPECIALIST])
        
        # Add intent-specific guidance
        if intents:
            intent_guidance = {
                IntentType.RESEARCH: "Prioritize finding current, authoritative sources.",
                IntentType.CRITIQUE: "Focus on identifying risks and improvement opportunities.",
                IntentType.GENERATE: "Emphasize creative and practical solution generation.",
                IntentType.VERIFY: "Double-check all claims and provide confidence assessments.",
                IntentType.DEBUG: "Use systematic troubleshooting methodologies.",
                IntentType.ANALYZE: "Provide deep analytical insights and breakdowns."
            }
            
            for intent in intents:
                if intent in intent_guidance:
                    prompt += f"\n\n**{intent.value.title()} Focus**: {intent_guidance[intent]}"
        
        return prompt
    
    def _build_agent_prompt(self, agent: SwarmAgent, user_query: str, context: str) -> str:
        """Build the full prompt for an agent including context and role guidance"""
        
        prompt_parts = []
        
        if context:
            prompt_parts.append(f"**Context from previous collaboration:**\n{context}\n")
        
        prompt_parts.append(f"**User Query:** {user_query}\n")
        
        prompt_parts.append(f"**Your Role:** {agent.role.value.replace('_', ' ').title()}")
        
        if agent.assigned_intents:
            intent_names = [intent.value.replace('_', ' ').title() for intent in agent.assigned_intents]
            prompt_parts.append(f"**Assigned Focus Areas:** {', '.join(intent_names)}")
        
        prompt_parts.append("""
**Instructions:**
1. Address the query from your specialized perspective
2. Provide concrete, actionable insights  
3. Include confidence levels for key claims
4. Note any contradictions or uncertainties
5. Be concise but thorough

Respond with your expert analysis:""")
        
        return "\n".join(prompt_parts)

    async def _resolve_conflicts(
        self, 
        executions: List[SwarmExecution], 
        user_query: str
    ) -> List[ConflictResolution]:
        """Use truth arbitrator to resolve conflicts between model outputs"""
        
        # Extract all substantive claims from executions
        claims = []
        for execution in executions:
            if execution.error or not execution.content:
                continue
            
            # Simple claim extraction (can be enhanced with NLP)
            sentences = execution.content.split('.')
            for sentence in sentences:
                if len(sentence.strip()) > 20:  # Filter out short fragments
                    claims.append({
                        'text': sentence.strip(),
                        'source_model': execution.agent.model_id,
                        'confidence': execution.confidence_score
                    })
        
        # Use truth arbitrator to resolve conflicts
        return await self.arbitrator.resolve_conflicts(claims, user_query)
    
    def _calculate_convergence(self, executions: List[SwarmExecution]) -> float:
        """Calculate how well the models agreed with each other"""
        
        valid_executions = [e for e in executions if not e.error and e.content]
        if len(valid_executions) < 2:
            return 1.0  # Single model or no valid results = perfect "convergence"
        
        # Simple semantic similarity approximation
        # In production, use embedding-based similarity
        
        similarity_scores = []
        contents = [e.content.lower() for e in valid_executions]
        
        for i in range(len(contents)):
            for j in range(i + 1, len(contents)):
                # Basic word overlap similarity
                words1 = set(contents[i].split())
                words2 = set(contents[j].split())
                
                intersection = len(words1 & words2)
                union = len(words1 | words2)
                
                if union > 0:
                    similarity = intersection / union
                    similarity_scores.append(similarity)
        
        return sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0.0
    
    async def _synthesize_outputs(
        self,
        executions: List[SwarmExecution],
        resolutions: List[ConflictResolution],
        user_query: str,
        api_keys: Dict[str, str]
    ) -> str:
        """Create final synthesized output from all agent executions"""
        
        # Use the best-performing execution as the synthesizer if possible
        synthesizer_execution = None
        for execution in executions:
            if (execution.agent.role == SwarmRole.SYNTHESIZER and 
                not execution.error and execution.content):
                synthesizer_execution = execution
                break
        
        if synthesizer_execution:
            return synthesizer_execution.content
        
        # Fallback: use highest-confidence execution with GPT-4 for synthesis
        valid_executions = [e for e in executions if not e.error and e.content]
        if not valid_executions:
            return "I apologize, but I encountered errors processing your request. Please try again."
        
        # Simple synthesis by combining top insights
        synthesis_parts = [f"**Original Query:** {user_query}\n"]
        
        # Add key insights from all agents
        all_insights = []
        for execution in valid_executions:
            if execution.key_insights:
                all_insights.extend(execution.key_insights)
        
        if all_insights:
            synthesis_parts.append("**Key Insights:**")
            for insight in all_insights[:5]:  # Top 5 insights
                synthesis_parts.append(f"• {insight}")
        
        # Add conflict resolutions
        if resolutions:
            synthesis_parts.append("\n**Resolved Considerations:**")
            for resolution in resolutions:
                synthesis_parts.append(f"• {resolution.final_verdict}")
        
        # Add best execution content
        best_execution = max(valid_executions, key=lambda e: e.confidence_score)
        synthesis_parts.append(f"\n**Primary Response:**\n{best_execution.content}")
        
        return "\n".join(synthesis_parts)
    
    async def _update_memory(
        self, 
        executions: List[SwarmExecution], 
        final_output: str,
        user_query: str
    ) -> List[Insight]:
        """Update memory lattice with new insights from this swarm execution"""
        
        insights = []
        
        for execution in executions:
            if execution.error or not execution.content:
                continue
                
            # Create insights from agent execution
            for insight_text in execution.key_insights:
                insight = Insight(
                    content=insight_text,
                    source_model=execution.agent.model_id,
                    confidence=execution.confidence_score,
                    intent_types=execution.agent.assigned_intents,
                    context=user_query
                )
                insights.append(insight)
                await self.memory.add_insight(insight)
        
        # Add final synthesis as insight
        final_insight = Insight(
            content=final_output,
            source_model="swarm_synthesis",
            confidence=0.95,
            intent_types=[],
            context=user_query
        )
        insights.append(final_insight)
        await self.memory.add_insight(final_insight)
        
        return insights
    
    def _calculate_performance_metrics(
        self, 
        executions: List[SwarmExecution], 
        total_time: float
    ) -> Dict[str, float]:
        """Calculate performance metrics for this swarm execution"""
        
        valid_executions = [e for e in executions if not e.error]
        
        if not valid_executions:
            return {"success_rate": 0.0, "avg_execution_time": total_time}
        
        return {
            "success_rate": len(valid_executions) / len(executions),
            "avg_execution_time": sum(e.execution_time_ms for e in valid_executions) / len(valid_executions),
            "avg_confidence": sum(e.confidence_score for e in valid_executions) / len(valid_executions),
            "total_insights": sum(len(e.key_insights) for e in valid_executions),
            "parallelization_efficiency": (sum(e.execution_time_ms for e in valid_executions) / len(valid_executions)) / total_time if total_time > 0 else 0
        }
    
    async def _fallback_execution(self, user_query: str, api_keys: Dict[str, str], error: str) -> SwarmResult:
        """Fallback to single model execution if swarm fails"""
        
        # Try to use GPT-4 as fallback
        if "openai" in api_keys:
            try:
                response = await call_openai(
                    messages=[{"role": "user", "content": user_query}],
                    model="gpt-4o",
                    api_key=api_keys["openai"],
                    temperature=0.7
                )
                
                fallback_agent = SwarmAgent(
                    model_id="gpt-4o",
                    provider="openai",
                    role=SwarmRole.SYNTHESIZER,
                    assigned_intents=[],
                    confidence_threshold=0.5,
                    execution_priority=1
                )
                
                fallback_execution = SwarmExecution(
                    agent=fallback_agent,
                    content=response.content,
                    execution_time_ms=1000,
                    confidence_score=0.7
                )
                
                return SwarmResult(
                    final_output=response.content,
                    all_executions=[fallback_execution],
                    convergence_score=1.0,
                    total_time_ms=1000,
                    swarm_composition=[fallback_agent],
                    conflict_resolutions=[],
                    performance_metrics={"success_rate": 1.0, "fallback_used": True},
                    memory_updates=[]
                )
            except Exception as fallback_error:
                logger.warning(f"Failed to create fallback swarm result: {fallback_error}")
                pass
        
        # Ultimate fallback
        return SwarmResult(
            final_output=f"I apologize, but I encountered technical difficulties: {error}. Please try your request again.",
            all_executions=[],
            convergence_score=0.0,
            total_time_ms=0,
            swarm_composition=[],
            conflict_resolutions=[],
            performance_metrics={"success_rate": 0.0, "error": error},
            memory_updates=[]
        )
    
    def _generate_swarm_id(self, user_query: str) -> str:
        """Generate unique ID for swarm execution tracking"""
        return hashlib.md5(f"{user_query}_{time.time()}".encode()).hexdigest()[:8]
    
    def _get_provider_for_model(self, model_id: str) -> str:
        """Map model IDs to providers"""
        provider_map = {
            "gpt-4o": "openai",
            "claude-3-5-sonnet": "anthropic", 
            "gemini-2.0-flash": "google",
            "sonar-pro": "perplexity",
            "kimi": "moonshot"
        }
        return provider_map.get(model_id, "openai")
    
    def _extract_insights(self, content: str, agent: SwarmAgent) -> Tuple[List[str], List[str], List[str]]:
        """Extract insights, contradictions, and citations from agent response"""
        
        # Simple keyword-based extraction (enhance with NLP in production)
        insights = []
        contradictions = []
        citations = []
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            
            # Extract insights
            if any(keyword in line.lower() for keyword in ['key insight:', 'important:', 'note that', 'critical']):
                insights.append(line)
            
            # Extract contradictions  
            if any(keyword in line.lower() for keyword in ['however', 'but', 'contradiction', 'conflict']):
                contradictions.append(line)
            
            # Extract citations (URLs)
            if 'http' in line:
                citations.append(line)
        
        return insights[:3], contradictions[:2], citations[:5]  # Limit quantities
    
    def _calculate_confidence(self, content: str, agent: SwarmAgent) -> float:
        """Calculate confidence score for agent response"""
        
        confidence = 0.5  # Base confidence
        
        # Length and detail bonus
        if len(content) > 200:
            confidence += 0.1
        if len(content) > 500:
            confidence += 0.1
        
        # Citation bonus
        if 'http' in content:
            confidence += 0.1
        
        # Uncertainty penalty
        uncertainty_words = ['might', 'possibly', 'perhaps', 'unclear', 'uncertain']
        uncertainty_count = sum(1 for word in uncertainty_words if word in content.lower())
        confidence -= uncertainty_count * 0.05
        
        # Role-specific adjustments
        if agent.role == SwarmRole.VERIFIER:
            confidence += 0.1  # Verifiers should be more confident
        elif agent.role == SwarmRole.CREATIVE:
            confidence -= 0.05  # Creative outputs are inherently uncertain
        
        return max(0.1, min(1.0, confidence))