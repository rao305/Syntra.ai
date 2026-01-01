"""
Multi-Agent Council Orchestrator - Main orchestration logic.

Orchestrates the three-phase workflow:
1. Phase 1: Parallel execution of 5 specialist agents
2. Phase 2: Debate Synthesizer merges outputs
3. Phase 3: Judge Agent produces final deliverable with verdict
"""

import asyncio
import logging
import time
import re
from typing import Dict, List, Optional, Literal, AsyncGenerator, Any
from dataclasses import dataclass
from datetime import datetime

from app.models.provider_key import ProviderType
from app.services.council.config import (
    OutputMode,
    TOKEN_LIMITS,
    AGENT_PROVIDER_MAPPING,
    get_model_for_provider,
)
from app.services.council.base import run_agent, get_available_providers
from app.services.provider_dispatch import call_provider_adapter
from app.services.routing_header import (
    RoutingHeaderInfo,
    build_routing_header,
    provider_name as _provider_name,
)
from app.services.council.agents import (
    ARCHITECT_PROMPT,
    DATA_ENGINEER_PROMPT,
    RESEARCHER_PROMPT,
    RED_TEAMER_PROMPT,
    OPTIMIZER_PROMPT,
    SYNTHESIZER_PROMPT,
    get_judge_prompt,
)
from app.services.council.agents.synthesizer import format_synthesizer_input
from app.services.council.agents.judge import format_judge_input
from app.services.council.base_system_prompt import (
    build_context_pack,
    inject_base_prompt
)
from app.services.council.quality_directive import (
    QUALITY_DIRECTIVE,
    get_role_specific_directive,
    inject_quality_directive
)
from app.services.council.query_classifier import (
    classify_query,
    QueryComplexity
)
from app.services.council.quality_validator import (
    validate_response_quality,
    QualityScores
)

logger = logging.getLogger(__name__)


@dataclass
class CouncilConfig:
    """Configuration for council execution."""
    query: str
    output_mode: OutputMode = OutputMode.DELIVERABLE_OWNERSHIP
    api_keys: Dict[str, str] = None  # {"openai": "key", "gemini": "key", ...}
    preferred_providers: Optional[Dict[str, ProviderType]] = None
    verbose: bool = True
    # Syntra SuperBenchmark features
    context_pack: Optional[Dict[str, Any]] = None  # Pre-built context pack dict
    lexicon_lock: Optional[Dict[str, List[str]]] = None  # {"allowed_terms": [...], "forbidden_terms": [...]}
    output_contract: Optional[Dict[str, Any]] = None  # {"required_headings": [...], "file_count": N, "format": "..."}
    transparency_mode: bool = False  # Whether to show internal stages/models
    # Quality directive features
    enable_quality_directive: bool = True  # Whether to inject quality directive
    enable_quality_validation: bool = True  # Whether to run quality validation after judge
    query_complexity: Optional[int] = None  # Manual complexity override (1-5), auto-detected if None


@dataclass
class CouncilOutput:
    """Output from council execution."""
    status: str  # "success" | "error"
    output: Optional[str] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None
    phase: Optional[str] = None  # Current phase during execution
    phase1_outputs: Optional[Dict[str, tuple[str, ProviderType]]] = None  # Optional: individual outputs


class CouncilOrchestrator:
    """Main orchestrator for Multi-Agent Council workflow."""

    def __init__(self):
        self.phases = {
            "phase_1": "Running 5 specialist agents in parallel",
            "phase_2": "Running Debate Synthesizer",
            "phase_3": "Running Judge Agent"
        }

    async def run(
        self,
        config: CouncilConfig,
        progress_callback=None  # Optional: async callback for progress
    ) -> CouncilOutput:
        """
        Execute the full Multi-Agent Council workflow.

        Args:
            config: CouncilConfig with query, output_mode, api_keys
            progress_callback: Optional async callback for progress updates

        Returns:
            CouncilOutput with final deliverable and metadata
        """
        start_time = time.perf_counter()

        if config.api_keys is None:
            return CouncilOutput(
                status="error",
                error="No API keys provided. Required: at least one of {openai, gemini, perplexity, kimi}"
            )

        try:
            if config.verbose:
                logger.info(
                    "🚀 Starting Multi-Agent Council",
                    extra={
                        "query_length": len(config.query),
                        "output_mode": config.output_mode.value
                    }
                )

            # Verify available providers
            available = get_available_providers(config.api_keys)
            if not available:
                return CouncilOutput(
                    status="error",
                    error="No valid API keys found. Available: openai, gemini, perplexity, kimi"
                )

            if config.verbose:
                logger.info(f"Available providers: {[p.value for p in available]}")

            # =====================================================================
            # QUERY COMPLEXITY CLASSIFICATION (for quality directive)
            # =====================================================================
            query_complexity = config.query_complexity
            if query_complexity is None and config.enable_quality_directive:
                # Auto-detect complexity if not manually specified
                query_complexity, complexity_reasoning = await classify_query(
                    query=config.query,
                    api_keys=config.api_keys,
                    use_llm=True  # Use LLM for accurate classification
                )
                if config.verbose:
                    logger.info(f"📊 Query classified as Level {query_complexity}/5: {complexity_reasoning}")
            else:
                query_complexity = query_complexity or 3  # Default to medium complexity

            # =====================================================================
            # PHASE 1: Run 5 agents in parallel
            # =====================================================================
            if progress_callback:
                await progress_callback({
                    "type": "phase_start",
                    "phase": "phase_1",
                    "message": self.phases["phase_1"]
                })

            if config.verbose:
                logger.info("⚡ Phase 1: Running 5 specialist agents in parallel...")

            phase_1_start = time.perf_counter()

            # Build context pack from config
            context_pack_str = None
            if config.context_pack:
                context_pack_str = build_context_pack(
                    goal=config.query,
                    locked_decisions=config.context_pack.get('locked_decisions'),
                    glossary=config.context_pack.get('glossary'),
                    lexicon_lock=config.lexicon_lock,
                    open_questions=config.context_pack.get('open_questions'),
                    output_contract=config.output_contract,
                    style_rules=config.context_pack.get('style_rules')
                )
            elif config.lexicon_lock or config.output_contract:
                # Build minimal context pack if only lexicon/output contract provided
                context_pack_str = build_context_pack(
                    goal=config.query,
                    lexicon_lock=config.lexicon_lock,
                    output_contract=config.output_contract
                )

            # Determine providers for each agent
            providers = config.preferred_providers or AGENT_PROVIDER_MAPPING

            # Helper function to wrap agent execution with progress callbacks
            async def run_agent_with_progress(
                agent_name: str,
                display_name: str,
                system_prompt: str,
                query: str,
                api_keys: Dict[str, str],
                preferred_provider=None
            ):
                """Run agent with start/complete callbacks and base prompt injection."""
                # Inject quality directive if enabled
                if config.enable_quality_directive:
                    role_directive = get_role_specific_directive(agent_name)
                    enhanced_system_prompt = inject_quality_directive(
                        agent_prompt=system_prompt,
                        role=agent_name,
                        query_complexity=query_complexity
                    )
                else:
                    enhanced_system_prompt = system_prompt

                # Inject base system prompt and context pack
                enhanced_prompt = inject_base_prompt(
                    agent_specific_prompt=enhanced_system_prompt,
                    context_pack=context_pack_str,
                    transparency_mode=config.transparency_mode,
                    quality_directive=QUALITY_DIRECTIVE if config.enable_quality_directive else None,
                    query_complexity=query_complexity if config.enable_quality_directive else None
                )
                # Send agent_start (with error handling to prevent blocking)
                if progress_callback:
                    try:
                        await progress_callback({
                            "type": "agent_start",
                            "agent": display_name
                        })
                    except Exception as e:
                        logger.warning(f"Progress callback failed for {display_name} start: {e}", exc_info=True)
                
                try:
                    # Add timeout protection (90 seconds per agent - should be enough with provider-level timeouts)
                    AGENT_TIMEOUT = 90  # 90 seconds (30s per provider * 3 providers max)
                    if config.verbose:
                        logger.info(f"Starting {display_name} with {AGENT_TIMEOUT}s timeout")
                    
                    result = await asyncio.wait_for(
                        run_agent(
                            agent_name, enhanced_prompt, query, api_keys, preferred_provider
                        ),
                        timeout=AGENT_TIMEOUT
                    )
                    response_text, provider = result
                    
                    if config.verbose:
                        logger.info(f"{display_name} completed successfully, output length: {len(response_text)}")
                    
                    # Send agent_complete with output (full output, not truncated)
                    if progress_callback:
                        try:
                            await progress_callback({
                                "type": "agent_complete",
                                "agent": display_name,
                                "output": response_text  # Send full output
                            })
                        except Exception as e:
                            logger.warning(f"Progress callback failed for {display_name} complete: {e}", exc_info=True)
                    
                    return result
                except asyncio.TimeoutError:
                    error_msg = f"{display_name} timed out after {AGENT_TIMEOUT} seconds"
                    logger.error(error_msg)
                    # Send agent error
                    if progress_callback:
                        await progress_callback({
                            "type": "agent_complete",
                            "agent": display_name,
                            "status": "error",
                            "output": f"Error: {error_msg}"
                        })
                    raise Exception(error_msg)
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"{display_name} failed: {error_msg}", exc_info=True)
                    # Send agent error (with error handling to prevent blocking)
                    if progress_callback:
                        try:
                            await progress_callback({
                                "type": "agent_complete",
                                "agent": display_name,
                                "status": "error",
                                "output": f"Error: {error_msg}"
                            })
                        except Exception as callback_error:
                            logger.warning(f"Progress callback failed for {display_name} error: {callback_error}", exc_info=True)
                    raise

            # Execute all agents in parallel with progress tracking
            agent_tasks = [
                run_agent_with_progress("architect", "Architect Agent", ARCHITECT_PROMPT, 
                                       config.query, config.api_keys, providers.get("architect")),
                run_agent_with_progress("data_engineer", "Data Engineer Agent", DATA_ENGINEER_PROMPT, 
                                       config.query, config.api_keys, providers.get("data_engineer")),
                run_agent_with_progress("researcher", "Researcher Agent", RESEARCHER_PROMPT, 
                                       config.query, config.api_keys, providers.get("researcher")),
                run_agent_with_progress("red_teamer", "Red Teamer Agent", RED_TEAMER_PROMPT, 
                                       config.query, config.api_keys, providers.get("red_teamer")),
                run_agent_with_progress("optimizer", "Optimizer Agent", OPTIMIZER_PROMPT, 
                                       config.query, config.api_keys, providers.get("optimizer")),
            ]

            if config.verbose:
                logger.info("Executing 5 agents in parallel...")
            
            results = await asyncio.gather(*agent_tasks, return_exceptions=True)

            # Check for errors and log them
            errors = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    agent_names = ["Architect Agent", "Data Engineer Agent", "Researcher Agent", "Red Teamer Agent", "Optimizer Agent"]
                    agent_name = agent_names[i]
                    error_msg = str(result)
                    logger.error(f"{agent_name} failed: {error_msg}")
                    errors.append(f"{agent_name}: {error_msg}")
            
            # If any agent failed, return error (but don't block on first error - gather already collected all)
            if errors:
                error_summary = "; ".join(errors)
                logger.error(f"Phase 1 failed with errors: {error_summary}")
                return CouncilOutput(
                    status="error",
                    error=f"One or more agents failed: {error_summary}"
                )

            architect_response, architect_provider = results[0]
            data_engineer_response, data_engineer_provider = results[1]
            researcher_response, researcher_provider = results[2]
            red_teamer_response, red_teamer_provider = results[3]
            optimizer_response, optimizer_provider = results[4]

            phase_1_duration = time.perf_counter() - phase_1_start

            if config.verbose:
                logger.info(
                    "✅ Phase 1 completed",
                    extra={
                        "duration_ms": int(phase_1_duration * 1000),
                        "architect": architect_provider.value,
                        "data_engineer": data_engineer_provider.value,
                        "researcher": researcher_provider.value,
                        "red_teamer": red_teamer_provider.value,
                        "optimizer": optimizer_provider.value,
                    }
                )

            # =====================================================================
            # PHASE 2: Run Debate Synthesizer
            # =====================================================================
            if progress_callback:
                await progress_callback({
                    "type": "phase_start",
                    "phase": "phase_2",
                    "message": self.phases["phase_2"]
                })

            if config.verbose:
                logger.info("🔄 Phase 2: Running Debate Synthesizer...")

            phase_2_start = time.perf_counter()

            synthesizer_input = format_synthesizer_input(
                query=config.query,
                architect_response=architect_response,
                data_engineer_response=data_engineer_response,
                researcher_response=researcher_response,
                red_teamer_response=red_teamer_response,
                optimizer_response=optimizer_response
            )

            # Log synthesizer input size for debugging
            synthesizer_input_size = len(synthesizer_input)
            if config.verbose:
                logger.info(
                    f"Debate Synthesizer input size: {synthesizer_input_size} characters",
                    extra={
                        "input_size": synthesizer_input_size,
                        "agent_outputs": {
                            "architect": len(architect_response),
                            "data_engineer": len(data_engineer_response),
                            "researcher": len(researcher_response),
                            "red_teamer": len(red_teamer_response),
                            "optimizer": len(optimizer_response)
                        }
                    }
                )

            # Send Debate Synthesizer agent_start
            if progress_callback:
                await progress_callback({
                    "type": "agent_start",
                    "agent": "Debate Synthesizer"
                })

            # Add timeout protection for Debate Synthesizer
            # Increased to 5 minutes to account for:
            # - Large input from 5 agents (90s provider timeout)
            # - Potential retries across multiple providers
            SYNTHESIZER_TIMEOUT = 300  # 5 minutes
            try:
                if config.verbose:
                    logger.info(f"Starting Debate Synthesizer with {SYNTHESIZER_TIMEOUT}s timeout")

                # Inject quality directive for synthesizer if enabled
                if config.enable_quality_directive:
                    synthesizer_prompt_with_quality = inject_quality_directive(
                        agent_prompt=SYNTHESIZER_PROMPT,
                        role="synthesizer",
                        query_complexity=query_complexity
                    )
                else:
                    synthesizer_prompt_with_quality = SYNTHESIZER_PROMPT

                # Inject base prompt for synthesizer
                synthesizer_enhanced_prompt = inject_base_prompt(
                    agent_specific_prompt=synthesizer_prompt_with_quality,
                    context_pack=context_pack_str,
                    transparency_mode=config.transparency_mode,
                    quality_directive=QUALITY_DIRECTIVE if config.enable_quality_directive else None,
                    query_complexity=query_complexity if config.enable_quality_directive else None
                )
                
                synthesis, synthesizer_provider = await asyncio.wait_for(
                    run_agent(
                        "synthesizer", synthesizer_enhanced_prompt, synthesizer_input, config.api_keys,
                        providers.get("synthesizer")
                    ),
                    timeout=SYNTHESIZER_TIMEOUT
                )

                if config.verbose:
                    logger.info(f"Debate Synthesizer completed successfully, output length: {len(synthesis)}")

                # Send Debate Synthesizer agent_complete
                if progress_callback:
                    await progress_callback({
                        "type": "agent_complete",
                        "agent": "Debate Synthesizer",
                        "output": synthesis  # Send full output
                    })
            except asyncio.TimeoutError:
                error_msg = f"Debate Synthesizer timed out after {SYNTHESIZER_TIMEOUT} seconds"
                logger.error(error_msg)
                # Send error to progress callback
                if progress_callback:
                    await progress_callback({
                        "type": "agent_complete",
                        "agent": "Debate Synthesizer",
                        "status": "error",
                        "output": f"Error: {error_msg}"
                    })
                raise Exception(error_msg)
            except Exception as e:
                error_msg = f"Debate Synthesizer failed: {str(e)}"
                logger.error(error_msg, exc_info=True)
                # Send error to progress callback
                if progress_callback:
                    await progress_callback({
                        "type": "agent_complete",
                        "agent": "Debate Synthesizer",
                        "status": "error",
                        "output": f"Error: {error_msg}"
                    })
                raise

            phase_2_duration = time.perf_counter() - phase_2_start

            if config.verbose:
                logger.info(
                    "✅ Phase 2 completed",
                    extra={
                        "duration_ms": int(phase_2_duration * 1000),
                        "provider": synthesizer_provider.value
                    }
                )

            # =====================================================================
            # PHASE 3: Run Judge Agent
            # =====================================================================
            if progress_callback:
                await progress_callback({
                    "type": "phase_start",
                    "phase": "phase_3",
                    "message": self.phases["phase_3"]
                })

            if config.verbose:
                logger.info("⚖️ Phase 3: Running Judge Agent...")

            phase_3_start = time.perf_counter()

            judge_input = format_judge_input(
                query=config.query,
                output_mode=config.output_mode.value,
                synthesis=synthesis,
                architect_response=architect_response,
                data_engineer_response=data_engineer_response,
                researcher_response=researcher_response,
                red_teamer_response=red_teamer_response,
                optimizer_response=optimizer_response
            )

            # Log judge input size for debugging
            judge_input_size = len(judge_input)
            if config.verbose:
                logger.info(
                    f"Judge Agent input size: {judge_input_size} characters",
                    extra={"input_size": judge_input_size}
                )

            # Send Judge Agent agent_start
            if progress_callback:
                await progress_callback({
                    "type": "agent_start",
                    "agent": "Judge Agent"
                })

            # Inject quality directive for judge if enabled
            judge_prompt = get_judge_prompt(config.output_mode.value)
            if config.enable_quality_directive:
                judge_prompt_with_quality = inject_quality_directive(
                    agent_prompt=judge_prompt,
                    role="judge",
                    query_complexity=query_complexity
                )
            else:
                judge_prompt_with_quality = judge_prompt

            # Inject base prompt for judge
            judge_enhanced_prompt = inject_base_prompt(
                agent_specific_prompt=judge_prompt_with_quality,
                context_pack=context_pack_str,
                transparency_mode=config.transparency_mode,
                quality_directive=QUALITY_DIRECTIVE if config.enable_quality_directive else None,
                query_complexity=query_complexity if config.enable_quality_directive else None
            )

            try:
                if config.verbose:
                    logger.info("Calling Judge Agent...")
                
                # Add timeout protection for Judge Agent
                # Increased to 7 minutes to account for large input and potential retries
                JUDGE_TIMEOUT = 420  # 7 minutes
                try:
                    raw_output, judge_provider = await asyncio.wait_for(
                        run_agent(
                            "judge", judge_enhanced_prompt, judge_input, config.api_keys,
                            providers.get("judge")
                        ),
                        timeout=JUDGE_TIMEOUT
                    )
                    # Clean the output to remove hard rules and internal structure for non-code tasks
                    final_output = _clean_user_facing_output(raw_output.strip(), config.query)
                except asyncio.TimeoutError:
                    error_msg = f"Judge Agent timed out after {JUDGE_TIMEOUT} seconds"
                    logger.error(error_msg)
                    raise Exception(error_msg)

                if config.verbose:
                    logger.info(
                        f"Judge Agent completed successfully, output length: {len(final_output)}",
                        extra={"output_length": len(final_output), "provider": judge_provider.value}
                    )

                # Send Judge Agent agent_complete
                if progress_callback:
                    await progress_callback({
                        "type": "agent_complete",
                        "agent": "Judge Agent",
                        "output": final_output  # Send full output
                    })

                # Also mark Final Answer as complete
                if progress_callback:
                    await progress_callback({
                        "type": "agent_complete",
                        "agent": "Final Answer",
                        "output": final_output
                    })
            except Exception as e:
                error_msg = f"Judge Agent failed: {str(e)}"
                logger.error(error_msg, exc_info=True)
                
                # Send error to progress callback
                if progress_callback:
                    await progress_callback({
                        "type": "agent_complete",
                        "agent": "Judge Agent",
                        "status": "error",
                        "output": f"Error: {error_msg}"
                    })
                    await progress_callback({
                        "type": "error",
                        "agent": "Judge Agent",
                        "error": error_msg
                    })
                
                # Re-raise to be caught by outer try/except
                raise

            phase_3_duration = time.perf_counter() - phase_3_start

            if config.verbose:
                logger.info(
                    "✅ Phase 3 completed",
                    extra={
                        "duration_ms": int(phase_3_duration * 1000),
                        "provider": judge_provider.value
                    }
                )

            # =====================================================================
            # QUALITY VALIDATION (if enabled)
            # =====================================================================
            quality_scores = None
            if config.enable_quality_validation:
                if progress_callback:
                    await progress_callback({
                        "type": "agent_start",
                        "agent": "Quality Validator"
                    })

                if config.verbose:
                    logger.info("🔍 Running Quality Validation...")

                validation_start = time.perf_counter()

                try:
                    validation_result = await validate_response_quality(
                        query=config.query,
                        response=final_output,
                        query_complexity=query_complexity,
                        api_keys=config.api_keys,
                        preferred_provider="openai"
                    )

                    quality_scores = validation_result.scores

                    if config.verbose:
                        logger.info(
                            f"Quality Scores: Substance={quality_scores.substance_score:.1f}, "
                            f"Completeness={quality_scores.completeness_score:.1f}, "
                            f"Depth={quality_scores.depth_score:.1f}, "
                            f"Accuracy={quality_scores.accuracy_score:.1f}, "
                            f"Overall={quality_scores.overall_score:.1f}"
                        )

                    # If quality validation failed and there are gaps, append additional content
                    if validation_result.needs_revision and validation_result.additional_content:
                        if config.verbose:
                            logger.warning(
                                f"Quality gate failed. Adding {len(validation_result.additional_content)} chars of additional content."
                            )
                        # Append the additional content to the final output
                        final_output += "\n\n" + validation_result.additional_content

                    # If quality gate still failed, log warning
                    if not quality_scores.quality_gate_passed:
                        # Safely convert gaps to strings, handling any non-string types
                        gaps_str = []
                        for gap in validation_result.gaps_identified:
                            if hasattr(gap, 'value'):
                                gaps_str.append(str(gap.value))
                            else:
                                gaps_str.append(str(gap))
                        
                        logger.warning(
                            f"Quality gate not passed. Gaps: {', '.join(gaps_str)}"
                        )

                    if progress_callback:
                        await progress_callback({
                            "type": "agent_complete",
                            "agent": "Quality Validator",
                            "output": f"Quality validation complete. Overall score: {quality_scores.overall_score:.1f}/10",
                            "scores": quality_scores.to_dict()
                        })

                except Exception as e:
                    logger.error(f"Quality validation failed: {e}", exc_info=True)
                    # Don't fail the entire council if quality validation fails
                    if progress_callback:
                        await progress_callback({
                            "type": "agent_complete",
                            "agent": "Quality Validator",
                            "status": "error",
                            "output": f"Quality validation error: {str(e)}"
                        })

                validation_duration = time.perf_counter() - validation_start
                if config.verbose:
                    logger.info(
                        f"Quality validation completed in {int(validation_duration * 1000)}ms"
                    )

            # =====================================================================
            # Return Result
            # =====================================================================
            total_time = time.perf_counter() - start_time

            if progress_callback:
                await progress_callback({
                    "type": "complete",
                    "status": "success",
                    "output": final_output,  # Include final output in complete event
                    "final_answer": final_output  # Also include as final_answer for compatibility
                })

            if config.verbose:
                logger.info(
                    "✅ Council complete",
                    extra={
                        "total_time_ms": int(total_time * 1000),
                        "phase_1_ms": int(phase_1_duration * 1000),
                        "phase_2_ms": int(phase_2_duration * 1000),
                        "phase_3_ms": int(phase_3_duration * 1000),
                    }
                )

            return CouncilOutput(
                status="success",
                output=final_output,
                execution_time_ms=int(total_time * 1000),
                phase1_outputs={
                    "architect": (architect_response, architect_provider),
                    "data_engineer": (data_engineer_response, data_engineer_provider),
                    "researcher": (researcher_response, researcher_provider),
                    "red_teamer": (red_teamer_response, red_teamer_provider),
                    "optimizer": (optimizer_response, optimizer_provider),
                }
            )

        except Exception as e:
            logger.error(f"Council execution failed: {str(e)}", exc_info=True)
            total_time = time.perf_counter() - start_time

            if progress_callback:
                await progress_callback({
                    "type": "error",
                    "error": str(e)
                })

            return CouncilOutput(
                status="error",
                error=str(e),
                execution_time_ms=int(total_time * 1000)
            )

    async def run_streaming(
        self,
        config: CouncilConfig
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute council with streaming output for better UX.

        Yields progress events and final output.
        """
        async def stream_callback(event):
            yield event

        # We'll run the council and yield progress events
        output = await self.run(config, progress_callback=lambda e: stream_callback(e))
        yield {"type": "final", "output": output}


# =============================================================================
# Day-1 Router Orchestrator (single-provider, with Context Pack + Lexicon Lock)
# =============================================================================

DAY1_ROUTER_SYSTEM_PROMPT = """You are the **Router Orchestrator** for a multi-provider assistant. Your job is to produce consistently high-quality answers while routing each user message to the best model/provider. You MUST preserve context across turns and prevent terminology drift, even when switching providers.

This Day‑1 version prioritizes three outcomes:
1) Context continuity (no “new chat” resets when switching providers)
2) Terminology consistency via a Lexicon Lock (no invented severities/roles, no drift)
3) Reliable user experience (no greetings unless user greeted; stable tone/format)

Hard rules:
- Do NOT open with “Hi”, “Hello”, “Hey”, or similar unless the user greeted first in THEIR most recent message.
- Obey the Lexicon Lock (do not use forbidden terms).
- Use the Context Pack as ground truth.
- Route to exactly ONE provider/model per user turn unless a repair/fallback is triggered.

Operating requirements:
- Every model call MUST include: this instruction, the Lexicon Lock block, and the Context Pack block.
- Validate output for greeting/forbidden tokens; if violated, perform one repair retry; if still violated, fallback to strongest model and retry once."""


_GREETING_PREFIX_RE = re.compile(
    r"^\s*(?:[#>*_`~\-\s]+)?\s*(hi|hello|hey|good\s+(?:morning|afternoon|evening))\b",
    flags=re.IGNORECASE,
)


def _user_greeted(text: str) -> bool:
    return bool(_GREETING_PREFIX_RE.search(text or ""))


def _starts_with_greeting(text: str) -> bool:
    return bool(_GREETING_PREFIX_RE.search(text or ""))


def _contains_forbidden_tokens(text: str, forbidden: List[str]) -> List[str]:
    if not text or not forbidden:
        return []
    lower = text.lower()
    hits: List[str] = []
    for token in forbidden:
        if not token:
            continue
        if token.lower() in lower:
            hits.append(token)
    return hits


def _clean_user_facing_output(output: str, query: str) -> str:
    """
    Clean the output to remove hard rules, internal structure, and markdown file references
    for non-code tasks. Only keep these for explicit code generation requests.
    """
    if not output:
        return output
    
    query_lower = query.lower()
    is_code_request = any(keyword in query_lower for keyword in [
        'code', 'file', 'script', 'program', 'function', 'class', 'import',
        'create a', 'write a', 'generate code', 'build a', 'implement',
        '.py', '.js', '.ts', '.java', '.cpp', '.go', '.rs'
    ])
    
    # For non-code requests, remove hard rules and internal structure
    if not is_code_request:
        lines = output.split('\n')
        cleaned_lines = []
        skip_section = False
        skip_hard_rules = False
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Skip hard rules section
            if 'hard rules' in line_lower or 'hard rule' in line_lower:
                skip_hard_rules = True
                continue
            
            if skip_hard_rules:
                # Stop skipping when we hit a new major section (## or #)
                if line.strip().startswith('##') or line.strip().startswith('#'):
                    skip_hard_rules = False
                else:
                    continue
            
            # Skip "Final Deliverable" section header for non-code
            if line_lower.startswith('## final deliverable') and not is_code_request:
                # Skip the section but keep content if it's actual content
                continue
            
            # Skip provenance/ownership tables for non-code
            if 'ownership & provenance' in line_lower or 'provenance' in line_lower:
                # Skip until next major section
                skip_section = True
                continue
            
            if skip_section:
                if line.strip().startswith('##') or line.strip().startswith('#'):
                    skip_section = False
                else:
                    continue
            
            # Remove markdown file references like "Research_Report.md" in headers
            if line.strip().startswith('###') and '.md' in line:
                # Replace with just the title without .md
                line = re.sub(r'`?([^`]+\.md)`?', r'\1'.replace('.md', ''), line)
            
            cleaned_lines.append(line)
        
        output = '\n'.join(cleaned_lines)
        
        # Remove any remaining hard rules patterns
        output = re.sub(r'\*\*HARD RULES.*?\*\*.*?(?=\n\n|\n#|$)', '', output, flags=re.DOTALL | re.IGNORECASE)
        output = re.sub(r'❌ CANNOT.*?\n', '', output, flags=re.IGNORECASE)
        output = re.sub(r'✅ CAN.*?\n', '', output, flags=re.IGNORECASE)
    
    return output.strip()


def _detect_incident_domain(text: str) -> bool:
    t = (text or "").lower()
    return any(
        k in t
        for k in [
            "incident",
            "postmortem",
            "sev",
            "severity",
            "on-call",
            "pager",
            "p1",
            "p2",
            "p3",
            "p0",
        ]
    )


def _explicitly_requests_p0_taxonomy(text: str) -> bool:
    t = (text or "").lower()
    return bool(re.search(r"\b(add|include|allow|enable)\s+p0\b", t))


@dataclass
class Day1LexiconLock:
    allowed: List[str]
    forbidden: List[str]

    def render(self) -> str:
        allowed_str = ", ".join(self.allowed) if self.allowed else "None"
        forbidden_str = ", ".join(self.forbidden) if self.forbidden else "None"
        return (
            "LEXICON LOCK (Day‑1)\n"
            f"- Allowed: {allowed_str}\n"
            f"- Forbidden: {forbidden_str}\n"
        )


@dataclass
class Day1ContextPack:
    conversation_goal: str
    locked_decisions: List[str]
    glossary: Dict[str, str]
    domain_lexicon_allowed: List[str]
    domain_lexicon_forbidden: List[str]
    open_questions: List[str]
    last_user_request: str

    def render(self) -> str:
        locked = "\n".join([f"  - {d}" for d in (self.locked_decisions or ["None"])])
        glossary_lines = (
            "\n".join([f"  - {k}: {v}" for k, v in (self.glossary or {}).items()])
            if self.glossary
            else "  - None"
        )
        open_q = "\n".join([f"  - {q}" for q in (self.open_questions or ["None"])])
        allowed_str = ", ".join(self.domain_lexicon_allowed) if self.domain_lexicon_allowed else "None"
        forbidden_str = ", ".join(self.domain_lexicon_forbidden) if self.domain_lexicon_forbidden else "None"
        return (
            "CONTEXT PACK (Canonical, Orchestrator-Owned)\n"
            f"- Goal: {self.conversation_goal}\n"
            "- Locked decisions:\n"
            f"{locked}\n"
            "- Glossary:\n"
            f"{glossary_lines}\n"
            "- Domain lexicon:\n"
            f"  - Allowed: {allowed_str}\n"
            f"  - Forbidden: {forbidden_str}\n"
            "- Open questions:\n"
            f"{open_q}\n"
            "- Last user request (verbatim):\n"
            f"  {self.last_user_request}\n"
            "- Style rules:\n"
            "  - No greetings unless user greeted first.\n"
            "  - Use consistent headings and terminology.\n"
            "  - Be concise and actionable.\n"
        )


@dataclass
class RouterConfig:
    """Configuration for Day-1 router execution."""

    query: str
    api_keys: Dict[str, str] = None  # {"openai": "key", "gemini": "key", ...}
    thread_id: Optional[str] = None  # Enables in-process Context Pack continuity
    preferred_provider: Optional[ProviderType] = None
    max_tokens: int = 2000
    transparent_routing: bool = False
    verbose: bool = True


@dataclass
class RouterOutput:
    """Output from Day-1 router execution."""

    status: str  # "success" | "error"
    output: Optional[str] = None
    error: Optional[str] = None
    provider: Optional[ProviderType] = None
    model: Optional[str] = None
    execution_time_ms: Optional[int] = None
    repaired: bool = False
    used_fallback: bool = False


@dataclass
class _RouterState:
    conversation_goal: str
    locked_decisions: List[str]
    glossary: Dict[str, str]
    open_questions: List[str]
    domain: str  # "general" | "incident_response"
    lexicon_allowed: List[str]
    lexicon_forbidden: List[str]


_ROUTER_STATE_BY_THREAD: Dict[str, _RouterState] = {}


def _get_or_init_state(thread_id: Optional[str], user_query: str) -> _RouterState:
    # Ephemeral state (no continuity) when thread_id is missing
    if not thread_id:
        return _RouterState(
            conversation_goal=f"Help the user with: {user_query[:140]}",
            locked_decisions=[],
            glossary={},
            open_questions=[],
            domain="general",
            lexicon_allowed=[],
            lexicon_forbidden=[],
        )

    state = _ROUTER_STATE_BY_THREAD.get(thread_id)
    if state is not None:
        return state

    state = _RouterState(
        conversation_goal=f"Help the user with: {user_query[:140]}",
        locked_decisions=[],
        glossary={},
        open_questions=[],
        domain="general",
        lexicon_allowed=[],
        lexicon_forbidden=[],
    )
    _ROUTER_STATE_BY_THREAD[thread_id] = state
    return state


def _choose_provider(user_query: str, available: List[ProviderType], preferred: Optional[ProviderType]) -> ProviderType:
    if preferred and preferred in available:
        return preferred

    t = (user_query or "").lower()

    # Simple heuristic routing (no extra LLM call).
    looks_like_code = any(k in t for k in ["python", "typescript", "tsx", "js", "bug", "stack trace", "traceback", "refactor", "test"])
    wants_web = any(k in t for k in ["latest", "today", "current", "news", "web", "search", "cite", "citation", "source"])

    if wants_web and ProviderType.PERPLEXITY in available:
        return ProviderType.PERPLEXITY
    if looks_like_code and ProviderType.OPENAI in available:
        return ProviderType.OPENAI
    if ProviderType.GEMINI in available:
        return ProviderType.GEMINI
    if ProviderType.OPENAI in available:
        return ProviderType.OPENAI
    return available[0]


def _route_reason_for_query(user_query: str) -> str:
    t = (user_query or "").lower()
    if any(k in t for k in ["latest", "today", "current", "news", "web", "search", "cite", "citation", "source"]):
        return "Web-research style query routed to a web-capable model."
    if any(k in t for k in ["python", "typescript", "tsx", "js", "bug", "stack trace", "traceback", "refactor", "test"]):
        return "Coding-focused query routed to a coding-strong model."
    return "General query routed via heuristic selection."


def _strongest_provider(available: List[ProviderType]) -> Optional[ProviderType]:
    for p in [ProviderType.OPENAI, ProviderType.GEMINI, ProviderType.PERPLEXITY, ProviderType.KIMI, ProviderType.OPENROUTER]:
        if p in available:
            return p
    return available[0] if available else None


class RouterOrchestrator:
    """
    Day-1 single-provider router with Context Pack + Lexicon Lock + drift repair.

    Notes:
    - This is intentionally separate from the Multi-Agent Council workflow.
    - Context Pack continuity is in-process only (via `thread_id`).
    """

    async def run(self, config: RouterConfig) -> RouterOutput:
        start_time = time.perf_counter()

        if config.api_keys is None:
            return RouterOutput(status="error", error="No API keys provided.")

        available = get_available_providers(config.api_keys)
        if not available:
            return RouterOutput(status="error", error="No valid API keys found.")

        state = _get_or_init_state(config.thread_id, config.query)

        # Domain selection + lexicon lock
        if _detect_incident_domain(config.query):
            state.domain = "incident_response"
            # Default incident taxonomy (P1-P3 only)
            state.lexicon_allowed = ["P1", "P2", "P3"]
            state.lexicon_forbidden = ["P0", "SEV0", "SEV-0", "Critical-0", "P4", "P5"]

            # Taxonomy expansion gate: confirm in one line, then persist.
            if _explicitly_requests_p0_taxonomy(config.query) and "P0" not in state.lexicon_allowed:
                state.lexicon_allowed = ["P0", "P1", "P2", "P3"]
                state.lexicon_forbidden = ["SEV0", "SEV-0", "Critical-0", "P4", "P5"]
                total_time = time.perf_counter() - start_time
                return RouterOutput(
                    status="success",
                    output="Updating severity taxonomy per your request: now includes P0–P3.",
                    execution_time_ms=int(total_time * 1000),
                    repaired=False,
                    used_fallback=False,
                )
        else:
            state.domain = "general"
            state.lexicon_allowed = []
            state.lexicon_forbidden = []

        # Build Context Pack + Lexicon Lock
        lexicon_lock = Day1LexiconLock(
            allowed=state.lexicon_allowed,
            forbidden=state.lexicon_forbidden,
        )
        ctx_pack = Day1ContextPack(
            conversation_goal=state.conversation_goal,
            locked_decisions=list(state.locked_decisions),
            glossary=dict(state.glossary),
            domain_lexicon_allowed=list(state.lexicon_allowed),
            domain_lexicon_forbidden=list(state.lexicon_forbidden),
            open_questions=list(state.open_questions),
            last_user_request=config.query,
        )

        # Provider/model selection (single provider for the turn).
        provider = _choose_provider(config.query, available, config.preferred_provider)
        api_key = config.api_keys.get(provider.value)
        if not api_key:
            provider = _strongest_provider(available)
            if not provider:
                return RouterOutput(status="error", error="No usable providers found.")
            api_key = config.api_keys.get(provider.value)
        model = get_model_for_provider(provider)
        route_reason = _route_reason_for_query(config.query)

        system_block = (
            f"{DAY1_ROUTER_SYSTEM_PROMPT}\n\n"
            f"{lexicon_lock.render()}\n"
            f"{ctx_pack.render()}"
        )

        async def _call_once(messages: List[Dict[str, str]]) -> str:
            resp = await call_provider_adapter(
                provider=provider,
                model=model,
                messages=messages,
                api_key=api_key,
                max_tokens=config.max_tokens,
            )
            return resp.content

        def _validate(text: str) -> Optional[str]:
            if not _user_greeted(config.query) and _starts_with_greeting(text):
                return "Greeting drift: response starts with greeting but user did not greet."
            forbidden_hits = _contains_forbidden_tokens(text, state.lexicon_forbidden)
            if forbidden_hits:
                return f"Lexicon drift: contains forbidden tokens: {', '.join(forbidden_hits)}"
            return None

        try:
            draft = await _call_once(
                [
                    {"role": "system", "content": system_block},
                    {"role": "user", "content": config.query},
                ]
            )
        except Exception as e:
            total_time = time.perf_counter() - start_time
            return RouterOutput(
                status="error",
                error=f"Provider call failed: {e}",
                provider=provider,
                model=model,
                execution_time_ms=int(total_time * 1000),
            )

        violation = _validate(draft)
        if not violation:
            total_time = time.perf_counter() - start_time
            output_text = draft
            if config.transparent_routing:
                header = build_routing_header(
                    RoutingHeaderInfo(
                        provider=_provider_name(provider),
                        model=model or "unknown",
                        route_reason=route_reason,
                        context="context_pack",
                        repair_attempts=0,
                        fallback_used="no",
                    )
                )
                output_text = f"{header}{output_text}"
            return RouterOutput(
                status="success",
                output=output_text,
                provider=provider,
                model=model,
                execution_time_ms=int(total_time * 1000),
                repaired=False,
                used_fallback=False,
            )

        # Repair: same provider once
        repair_instruction = (
            "Rewrite your previous answer to remove forbidden terms and remove greetings. "
            "Do not change meaning. Reuse the locked decisions."
        )
        try:
            repaired = await _call_once(
                [
                    {"role": "system", "content": system_block},
                    {"role": "assistant", "content": draft},
                    {"role": "user", "content": repair_instruction},
                ]
            )
        except Exception:
            repaired = draft

        violation = _validate(repaired)
        if not violation:
            total_time = time.perf_counter() - start_time
            output_text = repaired
            if config.transparent_routing:
                header = build_routing_header(
                    RoutingHeaderInfo(
                        provider=_provider_name(provider),
                        model=model or "unknown",
                        route_reason=route_reason,
                        context="context_pack",
                        repair_attempts=1,
                        fallback_used="no",
                    )
                )
                output_text = f"{header}{output_text}"
            return RouterOutput(
                status="success",
                output=output_text,
                provider=provider,
                model=model,
                execution_time_ms=int(total_time * 1000),
                repaired=True,
                used_fallback=False,
            )

        # Fallback: strongest available provider once
        fallback_provider = _strongest_provider([p for p in available if p != provider])
        if not fallback_provider:
            total_time = time.perf_counter() - start_time
            return RouterOutput(
                status="error",
                error=f"Drift repair failed: {violation}",
                provider=provider,
                model=model,
                execution_time_ms=int(total_time * 1000),
                repaired=True,
                used_fallback=False,
            )

        fallback_api_key = config.api_keys.get(fallback_provider.value)
        fallback_model = get_model_for_provider(fallback_provider)

        async def _call_fallback(messages: List[Dict[str, str]]) -> str:
            resp = await call_provider_adapter(
                provider=fallback_provider,
                model=fallback_model,
                messages=messages,
                api_key=fallback_api_key,
                max_tokens=config.max_tokens,
            )
            return resp.content

        try:
            fallback = await _call_fallback(
                [
                    {"role": "system", "content": system_block},
                    {"role": "assistant", "content": repaired},
                    {"role": "user", "content": repair_instruction},
                ]
            )
        except Exception as e:
            total_time = time.perf_counter() - start_time
            return RouterOutput(
                status="error",
                error=f"Fallback provider call failed: {e}",
                provider=fallback_provider,
                model=fallback_model,
                execution_time_ms=int(total_time * 1000),
                repaired=True,
                used_fallback=True,
            )

        violation = _validate(fallback)
        total_time = time.perf_counter() - start_time
        if violation:
            output_text = "Sorry — I can’t comply with the locked terminology constraints for this request. What exact taxonomy/terms should I use?"
            if config.transparent_routing:
                header = build_routing_header(
                    RoutingHeaderInfo(
                        provider=_provider_name(fallback_provider),
                        model=fallback_model or "unknown",
                        route_reason=route_reason,
                        context="context_pack",
                        repair_attempts=1,
                        fallback_used="yes",
                    )
                )
                output_text = f"{header}{output_text}"
            return RouterOutput(
                status="success",
                output=output_text,
                provider=fallback_provider,
                model=fallback_model,
                execution_time_ms=int(total_time * 1000),
                repaired=True,
                used_fallback=True,
            )

        output_text = fallback
        if config.transparent_routing:
            header = build_routing_header(
                RoutingHeaderInfo(
                    provider=_provider_name(fallback_provider),
                    model=fallback_model or "unknown",
                    route_reason=route_reason,
                    context="context_pack",
                    repair_attempts=1,
                    fallback_used="yes",
                )
            )
            output_text = f"{header}{output_text}"
        return RouterOutput(
            status="success",
            output=output_text,
            provider=fallback_provider,
            model=fallback_model,
            execution_time_ms=int(total_time * 1000),
            repaired=True,
            used_fallback=True,
        )
