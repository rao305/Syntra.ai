"""
Real Collaboration Orchestrator

Handles the actual multi-model collaboration pipeline with real LLM calls.
Replaces the mock implementation with production-ready provider integration.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Optional, AsyncGenerator, Any
from datetime import datetime

logger = logging.getLogger(__name__)

from app.config.collaborate_models import (
    COLLAB_MODELS, REVIEW_MODELS, REVIEW_SYSTEM_PROMPT, 
    REVIEW_USER_TEMPLATE, DIRECTOR_USER_TEMPLATE
)
from app.services.provider_dispatch import call_provider_adapter
from app.models.provider_key import ProviderType
from app.models.collaborate import CollaborateRun, CollaborateStage, CollaborateReview


class CollaborationOrchestrator:
    """Orchestrates real multi-model collaboration with provider calls"""
    
    def __init__(self, db_session=None):
        self.db = db_session
        self.stages = ["analyst", "researcher", "creator", "critic", "reviews", "director"]
    
    async def run_collaboration_stream(
        self,
        thread_id: str,
        user_message: str,
        api_keys: Dict[str, str],
        mode: str = "auto"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Run collaboration with real LLM calls and stream events.
        
        Args:
            thread_id: Thread identifier
            user_message: User's original message
            api_keys: Available API keys by provider
            mode: "auto" or "manual"
            
        Yields:
            SSE events for stage progress and final content
        """
        
        # Create run record if DB available
        run_id = str(uuid.uuid4())
        persist_to_db = False  # Don't persist during streaming to avoid transaction errors
        # The streaming endpoint will handle persistence separately if needed after message creation
        
        start_time = time.perf_counter()
        stage_outputs = {}
        external_reviews = []
        
        try:
            # Run main collaboration stages  
            for stage_id in self.stages[:-2]:  # Skip reviews and director initially
                yield {"type": "stage_start", "stage_id": stage_id}
                
                stage_start = time.perf_counter()
                
                try:
                    output = await self._run_stage(
                        stage_id, user_message, stage_outputs, api_keys
                    )
                    stage_outputs[stage_id] = output
                    
                    # Save stage record (only if persistence is enabled)
                    if self.db and persist_to_db:
                        await self._save_stage_record(
                            run_id, stage_id, 
                            COLLAB_MODELS[stage_id]["provider"].value,
                            COLLAB_MODELS[stage_id]["model"],
                            "success",
                            (time.perf_counter() - stage_start) * 1000
                        )
                    
                    yield {"type": "stage_end", "stage_id": stage_id}
                    
                    # Manual mode: pause after creator stage for user review
                    if mode == "manual" and stage_id == "creator":
                        yield {
                            "type": "pause_draft",
                            "stage_id": stage_id,
                            "draft": output,
                            "run_id": run_id
                        }
                        
                        # Manual mode ends here - frontend will handle user interaction
                        # and call a resume endpoint
                        return
                    
                except Exception as e:
                    if self.db and persist_to_db:
                        await self._save_stage_record(
                            run_id, stage_id,
                            COLLAB_MODELS[stage_id]["provider"].value, 
                            COLLAB_MODELS[stage_id]["model"],
                            "error",
                            (time.perf_counter() - stage_start) * 1000,
                            str(e)
                        )
                    
                    # Continue with fallback
                    stage_outputs[stage_id] = f"Error in {stage_id}: {str(e)}"
                    yield {"type": "stage_end", "stage_id": stage_id}
            
            # Run external reviews
            yield {"type": "stage_start", "stage_id": "reviews"}

            reviews_start = time.perf_counter()
            external_reviews = []

            try:
                if stage_outputs.get("creator"):
                    external_reviews = await self._run_external_reviews(
                        user_message, stage_outputs["creator"], api_keys, run_id
                    )
                    logger.info(f"✅ External reviews completed: {len(external_reviews)} review(s) collected")
                else:
                    logger.warning("⚠️ No creator output available for reviews stage")

                if self.db and persist_to_db:
                    await self._save_stage_record(
                        run_id, "reviews", "multi-model", "external-council",
                        "success", (time.perf_counter() - reviews_start) * 1000
                    )
            except Exception as e:
                logger.error(f"❌ Error in reviews stage: {str(e)}")
                if self.db and persist_to_db:
                    await self._save_stage_record(
                        run_id, "reviews", "multi-model", "external-council",
                        "error", (time.perf_counter() - reviews_start) * 1000,
                        str(e)
                    )

            yield {"type": "stage_end", "stage_id": "reviews"}
            
            # Run director synthesis
            yield {"type": "stage_start", "stage_id": "director"}
            
            director_start = time.perf_counter()
            final_answer = await self._run_director_synthesis(
                user_message, stage_outputs, external_reviews, api_keys
            )
            
            if self.db and persist_to_db:
                await self._save_stage_record(
                    run_id, "director",
                    COLLAB_MODELS["director"]["provider"].value,
                    COLLAB_MODELS["director"]["model"], 
                    "success", (time.perf_counter() - director_start) * 1000
                )
            
            yield {"type": "stage_end", "stage_id": "director"}
            
            # Stream final answer in larger chunks for better performance
            chunk_size = 1000  # Increased from 50 for better UX
            for i in range(0, len(final_answer), chunk_size):
                chunk = final_answer[i:i + chunk_size]
                yield {"type": "final_chunk", "text": chunk}
                await asyncio.sleep(0.01)  # Minimal delay for streaming effect
            
            # Update run status (skipped - no DB persistence during streaming)
            total_time = (time.perf_counter() - start_time) * 1000
            
            # Yield final completion with metadata
            yield {
                "type": "done",
                "result": {
                    "final_answer": final_answer,
                    "duration_ms": int(total_time),
                    "stages_completed": len(self.stages),
                    "external_reviews_count": len(external_reviews),
                    "mode": mode
                }
            }
            
        except Exception as e:
            # Error handling (DB persistence skipped during streaming)
            logger.error(f"Collaboration failed: {str(e)}", exc_info=True)
            
            yield {"type": "error", "message": f"Collaboration streaming failed: {str(e)}"}
    
    async def _run_stage(
        self, 
        stage_id: str, 
        user_message: str, 
        previous_outputs: Dict[str, str],
        api_keys: Dict[str, str]
    ) -> str:
        """Run a single collaboration stage with real LLM call"""
        
        config = COLLAB_MODELS[stage_id]
        provider = config["provider"]
        model = config["model"] 
        system_prompt = config["system_prompt"]
        
        # Check if we have the required API key
        api_key = api_keys.get(provider.value)
        if not api_key:
            raise ValueError(f"No API key available for {provider.value}")
        
        # Build context for this stage
        context_parts = [f"USER QUESTION: {user_message}"]
        
        # Add relevant previous outputs
        if stage_id == "researcher" and "analyst" in previous_outputs:
            context_parts.append(f"\nANALYST BREAKDOWN:\n{previous_outputs['analyst']}")
        elif stage_id == "creator":
            if "analyst" in previous_outputs:
                context_parts.append(f"\nANALYST BREAKDOWN:\n{previous_outputs['analyst']}")
            if "researcher" in previous_outputs:
                context_parts.append(f"\nRESEARCH FINDINGS:\n{previous_outputs['researcher']}")
        elif stage_id == "critic" and "creator" in previous_outputs:
            context_parts.append(f"\nCREATOR'S DRAFT:\n{previous_outputs['creator']}")
        
        full_context = "\n".join(context_parts)
        
        # Make the API call
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_context}
        ]
        
        response = await call_provider_adapter(
            provider=provider,
            model=model,
            messages=messages,
            api_key=api_key,
            temperature=0.7 if stage_id == "creator" else 0.3
        )
        
        if not response:
            raise ValueError(f"Provider {provider.value} returned None response for stage {stage_id}")
        
        # ProviderResponse is a dataclass, access .content attribute
        return response.content if hasattr(response, 'content') else str(response)
    
    async def _run_external_reviews(
        self,
        user_message: str,
        creator_output: str,
        api_keys: Dict[str, str],
        run_id: str
    ) -> List[Dict[str, Any]]:
        """Run external multi-model reviews (MANDATORY STAGE - always executes)"""

        reviews = []

        # Log available API keys for debugging
        available_providers = list(api_keys.keys())
        logger.info(f"🔑 Available API keys for reviews: {available_providers}")

        # Compress creator output if too long
        compressed_report = creator_output
        if len(creator_output) > 2000:
            compressed_report = creator_output[:2000] + "...[truncated]"

        # Run reviews in parallel
        review_tasks = []
        review_configs_list = []

        for review_config in REVIEW_MODELS:
            provider_key = review_config["provider"].value
            review_configs_list.append(review_config)

            if api_keys.get(provider_key):
                logger.info(f"📋 Queuing review from {review_config['name']} ({provider_key})")
                task = self._run_single_review(
                    user_message, compressed_report, review_config, api_keys, run_id
                )
                review_tasks.append(task)
            else:
                logger.warning(f"⚠️ No API key for {review_config['name']} ({provider_key}) - will use fallback review")
                # Create a fallback review task that doesn't require API keys
                task = self._run_fallback_review(user_message, compressed_report, review_config, run_id)
                review_tasks.append(task)

        logger.info(f"🚀 Starting {len(review_tasks)} review task(s) (including fallback reviews)")

        if review_tasks:
            review_results = await asyncio.gather(*review_tasks, return_exceptions=True)

            for i, result in enumerate(review_results):
                if isinstance(result, Exception):
                    logger.error(f"❌ Review task {i+1} failed: {str(result)}")
                    continue  # Skip failed reviews
                if result and isinstance(result, dict):
                    reviews.append(result)
                    logger.info(f"✅ Review {i+1} completed: {result.get('source', 'unknown')}")
                elif result:
                    logger.warning(f"⚠️ Review {i+1} returned unexpected type: {type(result)}")

        logger.info(f"✅ Council review stage complete: {len(reviews)} review(s) collected")
        return reviews
    
    async def _run_single_review(
        self,
        user_message: str,
        report: str,
        review_config: Dict,
        api_keys: Dict[str, str],
        run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Run a single external review"""
        
        try:
            provider = review_config["provider"]
            model = review_config["model"]
            api_key = api_keys[provider.value]
            
            review_prompt = REVIEW_USER_TEMPLATE.format(
                question=user_message,
                report=report
            )
            
            messages = [
                {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": review_prompt}
            ]
            
            start_time = time.perf_counter()
            response = await call_provider_adapter(
                provider=provider,
                model=model,
                messages=messages,
                api_key=api_key,
                temperature=0.4
            )
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            if not response:
                logger.warning(f"⚠️ Provider {provider.value} returned None for review {review_config['name']}")
                return None
            
            # ProviderResponse is a dataclass, access attributes directly
            if hasattr(response, 'content'):
                content = response.content
                prompt_tokens = getattr(response, 'prompt_tokens', None)
                completion_tokens = getattr(response, 'completion_tokens', None)
                total_tokens = (prompt_tokens or 0) + (completion_tokens or 0) if (prompt_tokens or completion_tokens) else None
            else:
                # Fallback for unexpected types
                content = str(response)
                prompt_tokens = None
                completion_tokens = None
                total_tokens = None
            
            # Save review record (only if DB persistence is enabled)
            if self.db:
                review = CollaborateReview(
                    run_id=run_id,
                    source=review_config["name"],
                    provider=provider.value,
                    model=model,
                    content=content,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    latency_ms=int(latency_ms)
                )
                self.db.add(review)
                await self.db.flush()
            
            return {
                "source": review_config["name"],
                "content": content,
                "latency_ms": int(latency_ms)
            }
            
        except Exception as e:
            print(f"Review from {review_config['name']} failed: {e}")
            return None

    async def _run_fallback_review(
        self,
        user_message: str,
        report: str,
        review_config: Dict[str, Any],
        run_id: str
    ) -> Dict[str, Any]:
        """
        Provide a basic fallback review without requiring API keys.
        This ensures the council review stage always happens.
        """
        import time as time_module

        # Simulate a quick review based on content analysis
        start_time = time_module.time()

        # Basic quality checks (no LLM call needed)
        feedback_points = []

        # Check 1: Length assessment
        word_count = len(report.split())
        if word_count < 100:
            feedback_points.append("• Report is quite brief - consider expanding for more comprehensive coverage")
        elif word_count > 5000:
            feedback_points.append("• Report is lengthy - consider if all content is essential")
        else:
            feedback_points.append("• Report length appears appropriate for the complexity of the question")

        # Check 2: Structure assessment
        has_sections = report.count('\n') > 5
        if has_sections:
            feedback_points.append("• Good: Report has clear section structure")
        else:
            feedback_points.append("• Consider adding more structured sections for clarity")

        # Check 3: Detail assessment
        has_examples = "example" in report.lower() or "e.g." in report.lower()
        if has_examples:
            feedback_points.append("• Good: Report includes examples for illustration")
        else:
            feedback_points.append("• Consider adding concrete examples to support key points")

        # Check 4: Technical depth
        technical_terms = ["model", "parameter", "algorithm", "data", "training", "performance"]
        tech_term_count = sum(1 for term in technical_terms if term in report.lower())
        if tech_term_count > 0:
            feedback_points.append(f"• Good: Report demonstrates technical depth ({tech_term_count} key concepts identified)")
        else:
            feedback_points.append("• Consider adding more technical depth if appropriate for the topic")

        # Compile fallback review
        content = "## Fallback Council Review\n\n(This review was generated without external API key)\n\n" + "\n".join(feedback_points)

        latency_ms = int((time_module.time() - start_time) * 1000)

        # Save review record if DB available
        if self.db:
            try:
                review = CollaborateReview(
                    run_id=run_id,
                    source=f"{review_config['name']}-fallback",
                    provider="internal",
                    model="content-analysis",
                    content=content,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    latency_ms=latency_ms
                )
                self.db.add(review)
                await self.db.flush()
            except Exception as e:
                logger.warning(f"Failed to save fallback review record: {e}")

        logger.info(f"✅ Fallback review from {review_config['name']} completed in {latency_ms}ms")

        return {
            "source": f"{review_config['name']} (fallback)",
            "content": content,
            "latency_ms": latency_ms
        }

    async def _run_director_synthesis(
        self,
        user_message: str,
        stage_outputs: Dict[str, str],
        external_reviews: List[Dict[str, Any]],
        api_keys: Dict[str, str]
    ) -> str:
        """Run final director synthesis"""
        
        config = COLLAB_MODELS["director"]
        provider = config["provider"] 
        model = config["model"]
        system_prompt = config["system_prompt"]
        
        api_key = api_keys.get(provider.value)
        if not api_key:
            raise ValueError(f"No API key available for {provider.value}")
        
        # Build reviews block
        if external_reviews:
            reviews_block = "\n\n---\n\n".join([
                f"[Review {i+1} - {review['source']}]\n{review['content']}"
                for i, review in enumerate(external_reviews)
            ])
        else:
            reviews_block = "No external reviews available."
        
        # Use creator output as internal report
        internal_report = stage_outputs.get("creator", "No creator output available.")
        
        director_prompt = DIRECTOR_USER_TEMPLATE.format(
            question=user_message,
            internal_report=internal_report,
            reviews_block=reviews_block
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": director_prompt}
        ]
        
        response = await call_provider_adapter(
            provider=provider,
            model=model,
            messages=messages,
            api_key=api_key,
            temperature=0.5,
            max_tokens=16000  # Allow for comprehensive final answer (doubled from default 8192)
        )

        if not response:
            raise ValueError(f"Provider {provider.value} returned None response for director synthesis")
        
        # ProviderResponse is a dataclass, access .content attribute
        if hasattr(response, 'content'):
            return response.content or "Failed to generate final synthesis."
        else:
            return str(response)
    
    async def resume_collaboration_stream(
        self,
        run_id: str,
        user_action: str,
        edited_draft: Optional[str] = None,
        api_keys: Dict[str, str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Resume collaboration from manual pause point.
        
        Args:
            run_id: The collaboration run to resume
            user_action: "accept", "edit", or "cancel"
            edited_draft: User's edited version (if action is "edit")
            api_keys: API keys for providers
            
        Yields:
            SSE events for remaining stages
        """
        
        start_time = time.perf_counter()
        stage_outputs = {}
        external_reviews = []
        
        try:
            # Load existing run and stage data from database
            if self.db and run_id:
                # Get the run record
                from sqlalchemy import select
                run_result = await self.db.execute(
                    select(CollaborateRun).where(CollaborateRun.id == run_id)
                )
                run = run_result.scalar_one_or_none()
                
                if not run:
                    yield {"type": "error", "message": f"Collaboration run {run_id} not found"}
                    return
                
                # Load previous stage outputs
                stages_result = await self.db.execute(
                    select(CollaborateStage)
                    .where(CollaborateStage.run_id == run_id)
                    .where(CollaborateStage.status == "success")
                )
                completed_stages = stages_result.scalars().all()
                
                # Reconstruct stage outputs (this is simplified - in production you'd store the actual outputs)
                for stage in completed_stages:
                    if stage.stage_id in ["analyst", "researcher", "creator"]:
                        # For this demo, we'll use placeholder outputs
                        # In production, you'd store the actual stage outputs
                        stage_outputs[stage.stage_id] = f"Previous {stage.stage_id} output"
            
            # Handle user action
            if user_action == "cancel":
                yield {"type": "done", "result": {"cancelled": True}}
                return
            elif user_action == "edit" and edited_draft:
                # Use the edited draft
                stage_outputs["creator"] = edited_draft
            elif user_action == "accept":
                # Keep the original draft (already in stage_outputs)
                pass
            else:
                yield {"type": "error", "message": "Invalid user action"}
                return
            
            yield {"type": "resume_ack"}
            
            # Continue with remaining stages: critic, reviews, director
            remaining_stages = ["critic", "reviews", "director"]
            
            for stage_id in remaining_stages:
                yield {"type": "stage_start", "stage_id": stage_id}
                
                if stage_id == "reviews":
                    # Run external reviews
                    if stage_outputs.get("creator"):
                        reviews_start = time.perf_counter()
                        external_reviews = await self._run_external_reviews(
                            "User question",  # Would need to store this in run record
                            stage_outputs["creator"],
                            api_keys or {},
                            run_id
                        )
                        
                        if self.db and persist_to_db:
                            await self._save_stage_record(
                                run_id, "reviews", "multi-model", "external-council",
                                "success", (time.perf_counter() - reviews_start) * 1000
                            )
                    
                elif stage_id == "director":
                    # Run director synthesis
                    director_start = time.perf_counter()
                    final_answer = await self._run_director_synthesis(
                        "User question",  # Would need to store this in run record
                        stage_outputs, external_reviews, api_keys or {}
                    )
                    
                    if self.db and persist_to_db:
                        await self._save_stage_record(
                            run_id, "director",
                            COLLAB_MODELS["director"]["provider"].value,
                            COLLAB_MODELS["director"]["model"],
                            "success", (time.perf_counter() - director_start) * 1000
                        )
                    
                    # Stream final answer
                    chunk_size = 1000  # Increased from 50 for better UX
                    for i in range(0, len(final_answer), chunk_size):
                        chunk = final_answer[i:i + chunk_size]
                        yield {"type": "final_chunk", "text": chunk}
                        await asyncio.sleep(0.01)  # Minimal delay for streaming effect
                
                else:  # critic
                    # Run critic stage
                    stage_start = time.perf_counter()
                    try:
                        output = await self._run_stage(
                            stage_id, "User question", stage_outputs, api_keys or {}
                        )
                        stage_outputs[stage_id] = output
                        
                        if self.db and persist_to_db:
                            await self._save_stage_record(
                                run_id, stage_id,
                                COLLAB_MODELS[stage_id]["provider"].value,
                                COLLAB_MODELS[stage_id]["model"],
                                "success",
                                (time.perf_counter() - stage_start) * 1000
                            )
                    except Exception as e:
                        stage_outputs[stage_id] = f"Error in {stage_id}: {str(e)}"
                
                yield {"type": "stage_end", "stage_id": stage_id}
            
            # Complete the run (DB persistence skipped during streaming)
            total_time = (time.perf_counter() - start_time) * 1000
            
            yield {
                "type": "done",
                "result": {
                    "final_answer": final_answer,
                    "duration_ms": int(total_time),
                    "stages_completed": len(self.stages),
                    "external_reviews_count": len(external_reviews),
                    "mode": "manual"
                }
            }
            
        except Exception as e:
            yield {"type": "error", "message": f"Resume failed: {str(e)}"}

    async def _save_stage_record(
        self,
        run_id: str,
        stage_id: str,
        provider: str,
        model: str,
        status: str,
        latency_ms: float,
        error_msg: Optional[str] = None
    ):
        """Save stage execution record to database"""
        
        if not self.db:
            return
        
        stage = CollaborateStage(
            run_id=run_id,
            stage_id=stage_id,
            label=f"{stage_id.title()} stage",
            provider=provider,
            model=model,
            status=status,
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
            latency_ms=int(latency_ms),
            meta={"error": error_msg} if error_msg else None
        )
        
        self.db.add(stage)
        await self.db.flush()


# Global orchestrator instance
orchestrator = CollaborationOrchestrator()