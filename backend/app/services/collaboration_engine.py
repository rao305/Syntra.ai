"""
Multi-Agent Collaboration Engine (anonymous 5-model pipeline)

Uses five randomly ordered models (based on available API keys) without exposing
fixed roles. The final model synthesizes all prior responses into the user-visible
answer. Supports conversation continuity with stored agent outputs for follow-up
questions.
"""

from typing import Dict, Any, List, Optional, Tuple
import time
import asyncio
import random
from dataclasses import dataclass
from enum import Enum

from app.models.provider_key import ProviderType
from app.adapters.openai_adapter import call_openai
from app.adapters.perplexity import call_perplexity
from app.adapters.gemini import call_gemini
from app.adapters.kimi import call_kimi

import logging
logger = logging.getLogger(__name__)


class AgentRole(Enum):
    ANALYST = "agent_analyst"
    RESEARCHER = "agent_researcher" 
    CREATOR = "agent_creator"
    CRITIC = "agent_critic"
    SYNTHESIZER = "agent_synth"


@dataclass
class AgentOutput:
    role: AgentRole
    provider: str
    content: str
    timestamp: float
    turn_id: str


@dataclass
class CollaborationResult:
    final_report: str
    agent_outputs: List[AgentOutput]
    total_time_ms: float
    turn_id: str


class CollaborationEngine:
    """Multi-agent collaboration orchestrator"""
    
    def __init__(self):
        # Available model configurations - we'll randomly select 5 from these
        self.available_models = [
            {"provider": ProviderType.OPENAI, "model": "gpt-4o", "label": "GPT-4"},
            {"provider": ProviderType.OPENAI, "model": "gpt-4o-mini", "label": "GPT-4 Mini"},
            {"provider": ProviderType.PERPLEXITY, "model": "sonar-pro", "label": "Perplexity Sonar"},
            {"provider": ProviderType.GEMINI, "model": "gemini-2.5-flash", "label": "Gemini Flash"},
            {"provider": ProviderType.KIMI, "model": "moonshot-v1-32k", "label": "Kimi Moonshot"},
            {"provider": ProviderType.OPENAI, "model": "gpt-4o", "label": "GPT-4 Enhanced"},
        ]

        # Legacy agent configs retained for direct answer mode compatibility
        self.agent_configs = {
            AgentRole.ANALYST: {
                "provider": ProviderType.GEMINI,
                "model": "gemini-2.5-flash",
                "system_prompt": self._get_analyst_prompt(),
            },
            AgentRole.RESEARCHER: {
                "provider": ProviderType.PERPLEXITY,
                "model": "sonar-pro",
                "system_prompt": self._get_researcher_prompt(),
            },
            AgentRole.CREATOR: {
                "provider": ProviderType.OPENAI,
                "model": "gpt-4o",
                "system_prompt": self._get_creator_prompt(),
            },
            AgentRole.CRITIC: {
                "provider": ProviderType.OPENAI,
                "model": "gpt-4o",
                "system_prompt": self._get_critic_prompt(),
            },
            AgentRole.SYNTHESIZER: {
                "provider": ProviderType.OPENAI,
                "model": "gpt-4o",
                "system_prompt": self._get_synthesizer_prompt(),
            },
        }
    
    def _get_anonymous_collaboration_models(self, api_keys: Dict[str, str]) -> List[Dict]:
        """
        Randomly select 5 models from available models based on available API keys.
        Returns anonymous model configurations without role assignments.
        """
        # Filter models by available API keys
        available_models = []
        for model_config in self.available_models:
            if model_config["provider"].value in api_keys:
                available_models.append(model_config)

        if not available_models:
            raise ValueError("No provider API keys available for collaboration")
        
        # Ensure we have at least 5 different configurations by duplicating if needed
        while len(available_models) < 5:
            available_models.extend(available_models[:5-len(available_models)])
        
        # Randomly select 5 models
        selected_models = random.sample(available_models, 5)
        
        return [
            {
                "provider": model["provider"],
                "model": model["model"],
                "label": model["label"],
                "system_prompt": self._get_generic_collaboration_prompt(i + 1)
            }
            for i, model in enumerate(selected_models)
        ]
    
    def _get_generic_collaboration_prompt(self, step: int) -> str:
        """Generic collaboration prompt that doesn't reveal specific roles"""
        return f"""You are Model {step} in a 5-model collaborative AI system.

Your task is to contribute unique insights and perspectives to help answer the user's question comprehensively.

Guidelines:
1. Build upon previous models' contributions when available
2. Provide your own distinct perspective and expertise
3. Be thorough but concise
4. Focus on adding value rather than repeating information
5. If this is the final step (step 5), synthesize all previous contributions into a comprehensive final answer

Provide your response in a clear, helpful format that advances the collaborative effort."""
    
    def _get_analyst_prompt(self) -> str:
        return """You are **DAC Analyst**, the first agent in a 5-agent collaboration.

Your role: Break down the user's query into structured analysis.

Output a concise analysis with these sections:
1. **Problem Breakdown** - Core components and scope
2. **User Archetypes** - Who would benefit from this solution
3. **Success Criteria** - What constitutes a good solution
4. **Structure Recommendation** - How the solution should be organized

Keep analysis under 300 words. Focus on clarity and actionable insights for the downstream agents."""

    def _get_researcher_prompt(self) -> str:
        return """You are **DAC Researcher**, the second agent in a 5-agent collaboration.

Your role: Find up-to-date web information and credible sources.

Based on the user query and analyst breakdown, research:
1. **Current State** - Latest developments, trends, or standards
2. **Best Practices** - Industry-accepted approaches
3. **Tools & Technologies** - Available solutions and frameworks
4. **Citations** - Include URLs and publication dates

Provide factual, current information with proper citations. Keep under 400 words."""

    def _get_creator_prompt(self) -> str:
        return """You are **DAC Creator**, the third agent in a 5-agent collaboration.

Your role: Draft the main solution based on analyst structure and researcher findings.

Create a comprehensive solution that includes:
1. **Core Implementation** - Main approach or code
2. **Architecture** - How components fit together  
3. **User Experience** - How users interact with the solution
4. **Technical Details** - Implementation specifics

Build on the analyst's structure and incorporate researcher's findings. Be practical and detailed."""

    def _get_critic_prompt(self) -> str:
        return """You are **DAC Critic**, the fourth agent in a 5-agent collaboration.

Your role: Identify flaws, risks, and improvements in the creator's solution.

Analyze the proposed solution for:
1. **Technical Flaws** - Implementation issues or bugs
2. **Security Risks** - Vulnerabilities or safety concerns  
3. **Scalability Issues** - Performance or growth problems
4. **Missing Elements** - What's been overlooked
5. **Improvement Suggestions** - Specific actionable fixes

Be constructive but thorough. Focus on making the solution better, not just finding problems."""

    def _get_synthesizer_prompt(self) -> str:
        return """You are **DAC Synthesizer**, the final report writer in a 5-agent collaboration.

Upstream agents:
- Analyst (Gemini) – problem breakdown, user archetypes, structure
- Researcher (Perplexity) – up-to-date web findings & citations
- Creator (GPT) – main solution draft
- Critic (GPT) – flaws, risks, missing perspectives, improvements

Your job is to write **ONE single, high-quality, long final answer** for the user.

### Requirements

1. **Integrate all agents**
   - Use the Analyst's structure for clarity
   - Use the Researcher's facts and URLs as the source of truth
   - Use the Creator's ideas as a starting point
   - Apply the Critic's feedback to FIX problems, not just repeat them

2. **Quality bar**
   - Must be clearly better than anything a single model could write alone
   - Feel like a team of experts collaborated and you're presenting their final report
   - Aim for thorough, detailed answers (unless user asks for brief)
   - High information density over length, but err on comprehensive responses

3. **Structure**
   - Start with short **Executive Summary** (3–8 bullets or 1–2 paragraphs)
   - Use clear sections with headings adapted to the task
   - For technical solutions: Problem Analysis, Research Insights, Solution Architecture, Implementation Details, Security Considerations, Performance & Scalability, Next Steps
   - Adapt section names to the specific request

4. **Tone & style**
   - Write as a single, unified voice
   - Do NOT mention "Analyst/Researcher/Creator/Critic" unless user asks about process
   - Clear, direct language for smart but non-expert users
   - Use citations naturally when research provides URLs

5. **Follow-up friendly**
   - Structure should support follow-up questions
   - Label lists and examples clearly for easy reference
   - Keep logical organization

Your output is the **final user-visible answer**. Treat it like a polished report."""

    async def collaborate(
        self, 
        user_query: str,
        turn_id: str,
        api_keys: Dict[str, str],
        collaboration_mode: bool = True
    ) -> CollaborationResult:
        """
        Run the anonymous 5-model collaboration pipeline.
        
        Args:
            user_query: The user's question/request
            turn_id: Unique identifier for this collaboration turn
            api_keys: Map of provider -> api_key
            collaboration_mode: If False, just return direct answer
            
        Returns:
            CollaborationResult with final report and agent outputs
        """
        start_time = time.perf_counter()
        agent_outputs = []
        
        if not collaboration_mode:
            # Direct answer mode - use a random model
            return await self._direct_answer_mode(user_query, turn_id, api_keys)
        
        # Get 5 randomly selected models
        selected_models = self._get_anonymous_collaboration_models(api_keys)
        
        # Run collaboration with 5 anonymous models
        for i, model_config in enumerate(selected_models):
            try:
                # Build context from previous models
                if i == 0:
                    context = f"User Query: {user_query}"
                elif i == 4:  # Final model - synthesize all previous responses
                    context = f"""Original user query: {user_query}

Previous AI responses to build upon:
"""
                    for j, prev_output in enumerate(agent_outputs):
                        context += f"\nModel {j + 1} Response:\n{prev_output.content}\n"
                        
                    context += "\nPlease synthesize all the above responses into a comprehensive, final answer for the user."
                else:
                    context = f"User Query: {user_query}\n\nPrevious AI Responses:\n"
                    for j, prev_output in enumerate(agent_outputs):
                        context += f"\nModel {j + 1}: {prev_output.content}\n"
                
                # Run the model
                output = await self._run_anonymous_model(
                    model_config,
                    user_query,
                    turn_id,
                    api_keys,
                    context,
                    step=i + 1
                )
                agent_outputs.append(output)
                
            except Exception as e:
                # Handle individual step failures gracefully
                step_num = i + 1
                provider_name = model_config["label"]
                error_message = f"Step {step_num} ({provider_name}) failed: {str(e)[:200]}..."
                
                # Create a fallback output for this step
                fallback_output = AgentOutput(
                    role=AgentRole.CREATOR,
                    provider=provider_name,
                    content=f"[Error in {provider_name}] Unable to generate response due to technical issues. Moving to next step.",
                    timestamp=time.perf_counter(),
                    turn_id=turn_id
                )
                agent_outputs.append(fallback_output)
                
                logger.error("⚠️ Collaboration step {step_num} failed: {error_message}")
                
                # If this is the final step and we have no successful outputs, provide a basic response
                if step_num == 5 and len([o for o in agent_outputs if not o.content.startswith("[Error")]) == 0:
                    # All steps failed, provide a basic fallback response
                    basic_response = AgentOutput(
                        role=AgentRole.SYNTHESIZER,
                        provider="Fallback System",
                        content=f"I apologize, but I'm experiencing technical difficulties with my collaboration system. However, I can still help with your query: {user_query}\n\nPlease try again in a moment, or rephrase your question if the issue persists.",
                        timestamp=time.perf_counter(),
                        turn_id=turn_id
                    )
                    agent_outputs[-1] = basic_response
        
        total_time_ms = (time.perf_counter() - start_time) * 1000
        
        # The final model's output is our synthesized response
        final_output = agent_outputs[-1] if agent_outputs else None
        
        return CollaborationResult(
            final_report=final_output.content if final_output else "No response generated",
            agent_outputs=agent_outputs,
            total_time_ms=total_time_ms,
            turn_id=turn_id
        )
    
    async def _direct_answer_mode(
        self,
        user_query: str,
        turn_id: str, 
        api_keys: Dict[str, str]
    ) -> CollaborationResult:
        """Direct answer without full collaboration pipeline"""
        start_time = time.perf_counter()
        
        creator_output = await self._run_agent(
            AgentRole.CREATOR,
            user_query,
            turn_id,
            api_keys,
            context=""
        )
        
        total_time_ms = (time.perf_counter() - start_time) * 1000
        
        return CollaborationResult(
            final_report=creator_output.content,
            agent_outputs=[creator_output],
            total_time_ms=total_time_ms,
            turn_id=turn_id
        )
    
    async def _run_anonymous_model(
        self,
        model_config: Dict,
        user_query: str,
        turn_id: str,
        api_keys: Dict[str, str],
        context: str,
        step: int
    ) -> AgentOutput:
        """Run an anonymous model with the given configuration"""
        provider = model_config["provider"]
        model = model_config["model"]
        system_prompt = model_config["system_prompt"]
        label = model_config["label"]
        
        # Get API key for this provider
        api_key = api_keys.get(provider.value)
        if not api_key:
            # Try to fallback to OpenAI if available
            fallback_key = api_keys.get(ProviderType.OPENAI.value)
            if fallback_key:
                provider = ProviderType.OPENAI
                model = "gpt-4o"
                api_key = fallback_key
                label = f"{label} (Fallback to OpenAI)"
            else:
                raise ValueError(f"No API key for provider {provider.value} and no OpenAI fallback available")
        
        # Build prompt
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ]
        
        # Call the appropriate provider
        if provider == ProviderType.OPENAI:
            response = await call_openai(
                messages=messages,
                model=model,
                api_key=api_key,
                temperature=0.7
            )
            content = response.content
            
        elif provider == ProviderType.GEMINI:
            response = await call_gemini(
                messages=messages,
                model=model,
                api_key=api_key
            )
            content = response.content
            
        elif provider == ProviderType.PERPLEXITY:
            # For Perplexity, use a search-focused prompt if it's one of the first few steps
            if step <= 2:
                search_prompt = f"Research and provide current information for: {context}"
            else:
                search_prompt = context
            response = await call_perplexity(
                messages=[{"role": "user", "content": search_prompt}],
                model=model,
                api_key=api_key
            )
            content = response.content
            
        elif provider == ProviderType.KIMI:
            response = await call_kimi(
                messages=messages,
                model=model,
                api_key=api_key,
                temperature=0.7
            )
            content = response.content
            
        else:
            # Fallback to OpenAI for unsupported providers
            response = await call_openai(
                messages=messages,
                model="gpt-4o",
                api_key=api_keys.get(ProviderType.OPENAI.value),
                temperature=0.7
            )
            content = response.content
        
        return AgentOutput(
            role=AgentRole.CREATOR,  # Use generic role for compatibility
            provider=f"{label}",  # Use the label instead of provider name
            content=content,
            timestamp=time.perf_counter(),
            turn_id=turn_id
        )
    
    async def _run_agent(
        self,
        role: AgentRole,
        user_query: str,
        turn_id: str,
        api_keys: Dict[str, str],
        context: str = ""
    ) -> AgentOutput:
        """Run a single agent with the specified role"""
        config = self.agent_configs[role]
        provider = config["provider"]
        model = config["model"]
        system_prompt = config["system_prompt"]
        
        # Get API key for this provider
        api_key = api_keys.get(provider.value)
        if not api_key:
            raise ValueError(f"No API key for provider {provider.value}")
        
        # Build prompt
        if context:
            full_prompt = f"{context}\n\nPlease analyze the above and provide your {role.value} perspective."
        else:
            full_prompt = user_query
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_prompt}
        ]
        
        # Call the appropriate provider
        start_time = time.perf_counter()
        
        if provider == ProviderType.OPENAI:
            response = await call_openai(
                messages=messages,
                model=model,
                api_key=api_key,
                temperature=0.7
            )
            content = response.content
            
        elif provider == ProviderType.GEMINI:
            response = await call_gemini(
                messages=messages,
                model=model,
                api_key=api_key
            )
            content = response.content
            
        elif provider == ProviderType.PERPLEXITY:
            # For Perplexity, use a search-focused prompt
            search_prompt = f"Research the following query and provide up-to-date information with citations:\n\n{full_prompt}"
            response = await call_perplexity(
                messages=[{"role": "user", "content": search_prompt}],
                model=model,
                api_key=api_key
            )
            content = response.content
            
        elif provider == ProviderType.KIMI:
            response = await call_kimi(
                messages=messages,
                model=model,
                api_key=api_key,
                temperature=0.7
            )
            content = response.content
            
        else:
            # Fallback to OpenAI for unsupported providers
            response = await call_openai(
                messages=messages,
                model="gpt-4o",
                api_key=api_keys.get(ProviderType.OPENAI.value),
                temperature=0.7
            )
            content = response.content
        
        return AgentOutput(
            role=role,
            provider=provider.value,
            content=content,
            timestamp=time.perf_counter(),
            turn_id=turn_id
        )


# Conversation storage for follow-up questions
class ConversationMemory:
    """Store agent outputs for follow-up questions"""
    
    def __init__(self):
        self._storage: Dict[str, List[AgentOutput]] = {}
    
    def store_collaboration(self, turn_id: str, agent_outputs: List[AgentOutput]):
        """Store all agent outputs for a collaboration turn"""
        self._storage[turn_id] = agent_outputs
    
    def get_agent_output(self, turn_id: str, role: AgentRole) -> Optional[AgentOutput]:
        """Get specific agent output from a turn"""
        outputs = self._storage.get(turn_id, [])
        for output in outputs:
            if output.role == role:
                return output
        return None
    
    def get_all_outputs(self, turn_id: str) -> List[AgentOutput]:
        """Get all agent outputs from a turn"""
        return self._storage.get(turn_id, [])
    
    def get_recent_outputs(self, limit: int = 5) -> List[AgentOutput]:
        """Get recent agent outputs across all turns"""
        all_outputs = []
        for outputs in self._storage.values():
            all_outputs.extend(outputs)
        
        # Sort by timestamp, most recent first
        all_outputs.sort(key=lambda x: x.timestamp, reverse=True)
        return all_outputs[:limit]


# Global memory instance
conversation_memory = ConversationMemory()
