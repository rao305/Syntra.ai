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
from typing import Dict, List, Optional, Literal, AsyncGenerator, Any
from dataclasses import dataclass
from datetime import datetime

from app.models.provider_key import ProviderType
from app.services.council.config import OutputMode, TOKEN_LIMITS, AGENT_PROVIDER_MAPPING
from app.services.council.base import run_agent, get_available_providers
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

logger = logging.getLogger(__name__)


@dataclass
class CouncilConfig:
    """Configuration for council execution."""
    query: str
    output_mode: OutputMode = OutputMode.DELIVERABLE_OWNERSHIP
    api_keys: Dict[str, str] = None  # {"openai": "key", "gemini": "key", ...}
    preferred_providers: Optional[Dict[str, ProviderType]] = None
    verbose: bool = True


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
                """Run agent with start/complete callbacks."""
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
                            agent_name, system_prompt, query, api_keys, preferred_provider
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

            # Send Debate Synthesizer agent_start
            if progress_callback:
                await progress_callback({
                    "type": "agent_start",
                    "agent": "Debate Synthesizer"
                })

            synthesis, synthesizer_provider = await run_agent(
                "synthesizer", SYNTHESIZER_PROMPT, synthesizer_input, config.api_keys,
                providers.get("synthesizer")
            )

            # Send Debate Synthesizer agent_complete
            if progress_callback:
                await progress_callback({
                    "type": "agent_complete",
                    "agent": "Debate Synthesizer",
                    "output": synthesis  # Send full output
                })

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

            try:
                if config.verbose:
                    logger.info("Calling Judge Agent...")
                
                # Add timeout protection for Judge Agent (5 minutes max)
                JUDGE_TIMEOUT = 300  # 5 minutes
                try:
                    final_output, judge_provider = await asyncio.wait_for(
                        run_agent(
                            "judge", get_judge_prompt(config.output_mode.value), judge_input, config.api_keys,
                            providers.get("judge")
                        ),
                        timeout=JUDGE_TIMEOUT
                    )
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
            # Return Result
            # =====================================================================
            total_time = time.perf_counter() - start_time

            if progress_callback:
                await progress_callback({
                    "type": "complete",
                    "status": "success"
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
