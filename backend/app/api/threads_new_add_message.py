# New clean add_message implementation using proper coalescing

@router.post("/{thread_id}/messages", response_model=AddMessageResponse)
async def add_message(
    thread_id: str,
    request: AddMessageRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """Add a message to a thread and fan out to the selected provider.
    
    Uses request coalescing: identical concurrent requests share a single provider call.
    Only the leader writes to the database; followers return the leader's result.
    """
    await set_rls_context(db, org_id)
    await memory_guard.ensure_health()

    thread = await _get_thread(db, thread_id, org_id)

    org = await _get_org(db, org_id)
    request_limit = org.requests_per_day or settings.default_requests_per_day
    token_limit = org.tokens_per_day or settings.default_tokens_per_day

    # Use centralized context builder to ensure proper context handling
    # (includes system prompts, memory retrieval, query rewriting, etc.)
    from app.services.context_builder import context_builder
    from app.services.syntra_persona import SYNTRA_SYSTEM_PROMPT

    # Prepare attachments if present in the request
    attachments = None
    if hasattr(request, 'attachments') and request.attachments:
        attachments = [
            {
                "type": a.type,
                "data": a.data,
                "mimeType": a.mimeType
            }
            for a in request.attachments
        ]

    # Build contextual messages with full context support
    context_result = await context_builder.build_contextual_messages(
        db=db,
        thread_id=thread_id,
        user_id=request.user_id,
        org_id=org_id,
        latest_user_message=request.content,
        provider=request.provider,
        use_memory=True,
        use_query_rewriter=True,
        base_system_prompt=SYNTRA_SYSTEM_PROMPT,
        attachments=attachments
    )

    prompt_messages = context_result.messages
    prompt_tokens_estimate = estimate_messages_tokens(prompt_messages)

    await enforce_limits(
        org_id,
        request.provider,
        prompt_tokens_estimate,
        request_limit,
        token_limit,
    )

    api_key = await get_api_key_for_org(db, org_id, request.provider)

    # Validate and potentially correct the model before calling
    validated_model = validate_and_get_model(request.provider, request.model)
    current_model = validated_model

    # Generate coalesce key from provider, model, and full conversation
    coal_key = coalesce_key(
        request.provider.value,
        current_model,
        prompt_messages
    )

    # Start performance tracking
    perf_metrics = performance_monitor.start_request(
        provider=request.provider.value,
        model=current_model,
        thread_id=thread_id,
        user_id=request.user_id,
        streaming=False,
    )

    # Leader function: makes provider call and writes to DB once
    async def leader_make():
        """Leader: call provider and save to DB. Returns normalized response."""
        start_time = time.perf_counter()
        queue_wait_ms = 0
        
        # Retry logic
        max_retries = 2
        base_delay = 1.0
        provider_response = None
        current_attempt_model = current_model
        
        for attempt in range(max_retries):
            try:
                # Use pacer to manage rate limits
                pacer = build_pacer(request.provider.value)
                async with pacer as slot:
                    queue_wait_ms = slot.queue_wait_ms
                    provider_response = await call_provider_adapter(
                        request.provider,
                        current_attempt_model,
                        prompt_messages,
                        api_key,
                    )
                # Mark TTFT
                perf_metrics.mark_ttft()
                break  # Success
                
            except ProviderAdapterError as exc:
                perf_metrics.retry_count = attempt + 1
                error_str = str(exc).lower()
                
                is_model_error = any(
                    keyword in error_str 
                    for keyword in ["invalid model", "model not found", "no endpoints", "model unavailable", "permitted models"]
                )
                
                is_rate_limit = any(
                    keyword in error_str
                    for keyword in ["rate limit", "429", "too many requests", "quota"]
                )
                
                # Rate limit - exponential backoff
                if is_rate_limit and attempt < max_retries - 1:
                    delay = min(base_delay * (2 ** attempt), 8.0)
                    await asyncio.sleep(delay)
                    continue
                
                # Model error - try fallback
                if is_model_error and attempt < max_retries - 1:
                    fallback_model = get_fallback_model(request.provider, current_attempt_model)
                    if fallback_model and fallback_model != current_attempt_model:
                        from app.services.model_registry import is_valid_model
                        if is_valid_model(request.provider, fallback_model):
                            current_attempt_model = fallback_model
                            await asyncio.sleep(0.5)
                            continue
                
                # No more retries
                perf_metrics.error = str(exc)
                perf_metrics.mark_end()
                await performance_monitor.record_metrics(perf_metrics)
                
                status_code = status.HTTP_429_TOO_MANY_REQUESTS if is_rate_limit else status.HTTP_502_BAD_GATEWAY
                raise HTTPException(status_code=status_code, detail=str(exc)) from exc
        
        if provider_response is None:
            perf_metrics.error = "No response after retries"
            perf_metrics.mark_end()
            await performance_monitor.record_metrics(perf_metrics)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to get response from {request.provider.value} after {max_retries} attempts",
            )
        
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Calculate tokens
        actual_prompt_tokens = provider_response.prompt_tokens or prompt_tokens_estimate
        completion_tokens = provider_response.completion_tokens or estimate_text_tokens(provider_response.content)
        total_tokens = (actual_prompt_tokens or 0) + (completion_tokens or 0)
        
        # Record additional tokens if needed
        additional_tokens = max(total_tokens - prompt_tokens_estimate, 0)
        if additional_tokens:
            await record_additional_tokens(org_id, request.provider, additional_tokens)
        
        # Save messages to DB (LEADER ONLY)
        user_msg, assistant_msg = await _save_turn_to_db(
            db=db,
            thread_id=thread_id,
            user_id=request.user_id,
            user_content=request.content,
            assistant_content=provider_response.content,
            provider=request.provider.value,
            model=current_attempt_model,
            reason=request.reason,
            scope=request.scope.value,
            prompt_messages=prompt_messages,
            provider_response=provider_response,
            request=request,
            prompt_tokens_estimate=prompt_tokens_estimate,
        )
        
        # Complete performance tracking
        perf_metrics.mark_end()
        perf_metrics.prompt_tokens = actual_prompt_tokens
        perf_metrics.completion_tokens = completion_tokens
        perf_metrics.total_tokens = total_tokens
        perf_metrics.queue_wait_ms = queue_wait_ms
        await performance_monitor.record_metrics(perf_metrics)
        
        # Return normalized response (followers will reuse this)
        return {
            "user_message": _to_message_response(user_msg),
            "assistant_message": _to_message_response(assistant_msg),
            "router": {
                "provider": request.provider.value,
                "model": current_attempt_model,
                "reason": request.reason,
            }
        }, {"latency_ms": latency_ms, "queue_wait_ms": queue_wait_ms}
    
    # Run with coalescing - only leader does the work
    try:
        response_data, meta = await coalescer.run(coal_key, leader_make)
    except HTTPException:
        raise
    except Exception as e:
        perf_metrics.error = str(e)
        perf_metrics.mark_end()
        await performance_monitor.record_metrics(perf_metrics)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}"
        )
    
    # Both leader and followers return the same response
    return AddMessageResponse(
        user_message=response_data["user_message"],
        assistant_message=response_data["assistant_message"],
        router=RouterDecision(**response_data["router"]),
    )

