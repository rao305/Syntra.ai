# Integrate Enhanced Collaboration into /collaborate Function

This guide shows how to integrate all the enhanced collaboration features (Anonymous AI, Enhanced Thinking, Next-Gen Swarming) into your existing `/collaborate` API endpoint.

## 🎯 **Current Flow vs Enhanced Flow**

### **Current Flow:**
```
User → /collaborate endpoint → main_assistant.handle_message() → CollaborationEngine → 5-agent sequential
```

### **Enhanced Flow:**
```
User → /collaborate endpoint → enhanced_main_assistant.handle_message() → Strategy Selection → Multiple Engines:
  ├─ Anonymous Collaboration (bias-free)
  ├─ Enhanced Thinking (shared reasoning)  
  ├─ Next-Gen Swarming (intelligent coordination)
  └─ Legacy Sequential (backward compatibility)
```

---

## 🚀 **Integration Options**

### **Option 1: Full Replacement (Recommended)**

Replace the current collaboration system with the enhanced version:

```python
# In app/api/collaboration.py

# Replace this import:
# from app.services.main_assistant import main_assistant

# With this:
from app.services.enhanced_main_assistant import enhanced_main_assistant

# Update the collaborate endpoint:
@router.post("/collaborate")
async def collaborate(
    request: CollaborationRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Enhanced multi-agent collaboration with multiple strategies:
    - Anonymous collaboration (bias-free selection)
    - Enhanced thinking (shared reasoning processes)
    - Next-gen swarming (intelligent coordination)
    - Legacy sequential (backward compatibility)
    """
    await set_rls_context(db, org_id)
    
    # Collect API keys (same as before)
    api_keys = {}
    for provider in [ProviderType.OPENAI, ProviderType.GEMINI, ProviderType.PERPLEXITY]:
        try:
            key = await get_api_key_for_org(db, org_id, provider)
            if key:
                api_keys[provider.value] = key
        except Exception:
            continue
    
    if not api_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No API keys configured for collaboration providers"
        )
    
    # Generate turn ID
    import uuid
    turn_id = str(uuid.uuid4())
    
    # Get chat history (same as before)
    chat_history = []
    if request.thread_id:
        storage_service = ConversationStorageService(db)
        stored_turns = storage_service.get_thread_history(request.thread_id)
        for turn in stored_turns:
            chat_history.extend([
                {"role": "user", "content": turn.user_query},
                {"role": "assistant", "content": turn.final_report}
            ])
    
    # 🎉 ENHANCED COLLABORATION - Auto-selects best strategy
    result = await enhanced_main_assistant.handle_message(
        user_message=request.message,
        turn_id=turn_id,
        api_keys=api_keys,
        collaboration_mode=True,
        chat_history=chat_history,
        # collaboration_strategy=None,  # Auto-select based on query
        user_preferences=None  # Could add user preferences here
    )
    
    # Enhanced response with strategy information
    return {
        "final_report": result["content"],
        "collaboration_strategy": result["collaboration_strategy"],
        "turn_id": turn_id,
        
        # Strategy-specific information
        "quality_metrics": result.get("quality_metrics"),
        "bias_elimination_report": result.get("bias_elimination_report"),
        "thinking_journey": result.get("thinking_journey"),
        "collaboration_quality_score": result.get("collaboration_quality_score"),
        
        # Backward compatibility
        "agent_outputs": result.get("agent_outputs", []),
        "total_time_ms": result["total_time_ms"]
    }
```

### **Option 2: Hybrid Integration (Safe Migration)**

Keep both systems and select based on request parameters:

```python
# Add to CollaborationRequest model
class CollaborationRequest(BaseModel):
    user_id: Optional[str] = None
    message: str = Field(..., description="User's message or question")
    thread_id: Optional[str] = Field(None, description="Thread ID for context")
    
    # Enhanced collaboration options
    collaboration_strategy: Optional[str] = Field(None, description="Strategy: auto, anonymous, enhanced, nextgen, legacy")
    enable_anonymous: Optional[bool] = Field(False, description="Enable anonymous collaboration")
    show_thinking: Optional[bool] = Field(False, description="Show thinking processes")

@router.post("/collaborate") 
async def collaborate(
    request: CollaborationRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    # ... same setup as before ...
    
    # Choose collaboration system
    if request.collaboration_strategy or request.enable_anonymous or request.show_thinking:
        # Use enhanced collaboration
        from app.services.enhanced_main_assistant import enhanced_main_assistant
        
        # Map strategy
        strategy = None
        if request.enable_anonymous:
            strategy = "anonymous"
        elif request.collaboration_strategy:
            strategy = request.collaboration_strategy
        
        result = await enhanced_main_assistant.handle_message(
            user_message=request.message,
            turn_id=turn_id,
            api_keys=api_keys,
            collaboration_mode=True,
            chat_history=chat_history,
            collaboration_strategy=CollaborationStrategy(strategy) if strategy and strategy != "auto" else None,
            user_preferences={"show_thinking": request.show_thinking}
        )
        
        return {
            "final_report": result["content"],
            "collaboration_strategy": result["collaboration_strategy"],
            "enhanced_features": True,
            # ... include enhanced data ...
        }
    else:
        # Use legacy collaboration
        from app.services.main_assistant import main_assistant
        
        result = await main_assistant.handle_message(
            user_message=request.message,
            turn_id=turn_id,
            api_keys=api_keys,
            collaboration_mode=True,
            chat_history=chat_history
        )
        
        return {
            "final_report": result["content"],
            "collaboration_strategy": "legacy",
            "enhanced_features": False,
            # ... legacy format ...
        }
```

### **Option 3: A/B Testing Integration**

Test enhanced vs legacy collaboration:

```python
@router.post("/collaborate")
async def collaborate(
    request: CollaborationRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db)
):
    # ... same setup ...
    
    # A/B test enhanced collaboration
    use_enhanced = hash(request.user_id or turn_id) % 2 == 0
    
    if use_enhanced:
        # Enhanced collaboration
        from app.services.enhanced_main_assistant import enhanced_main_assistant
        result = await enhanced_main_assistant.handle_message(...)
        
        # Track metrics
        track_collaboration_metric("enhanced", result["collaboration_strategy"], result["total_time_ms"])
        
    else:
        # Legacy collaboration  
        from app.services.main_assistant import main_assistant
        result = await main_assistant.handle_message(...)
        
        # Track metrics
        track_collaboration_metric("legacy", "sequential", result.get("total_time_ms", 0))
    
    return result
```

---

## 🎛️ **Strategy Selection Guide**

### **Automatic Strategy Selection**

The enhanced system automatically selects the best strategy based on query analysis:

```python
# Query analysis determines strategy
"Compare these 3 options and recommend the best" 
→ ANONYMOUS (unbiased analysis needed)

"Explain step-by-step how this algorithm works"
→ ENHANCED_THINKING (deep reasoning needed)

"Design enterprise architecture for our platform"  
→ NEXTGEN_SWARM (intelligent coordination needed)

"What are the benefits of React hooks?"
→ LEGACY_SEQUENTIAL (simple query)
```

### **Manual Strategy Selection**

Users can explicitly request specific strategies:

```python
# Anonymous collaboration
POST /collaborate
{
  "message": "Analyze our product strategy",
  "collaboration_strategy": "anonymous",
  "enable_anonymous": true
}

# Enhanced thinking
POST /collaborate  
{
  "message": "Help me understand machine learning",
  "collaboration_strategy": "enhanced",
  "show_thinking": true
}

# Next-gen swarming
POST /collaborate
{
  "message": "Build comprehensive user onboarding",
  "collaboration_strategy": "nextgen" 
}

# Legacy sequential
POST /collaborate
{
  "message": "Simple question about JavaScript",
  "collaboration_strategy": "legacy"
}
```

---

## 📊 **Enhanced Response Format**

### **Anonymous Collaboration Response:**
```json
{
  "final_report": "Comprehensive analysis with unbiased recommendations...",
  "collaboration_strategy": "anonymous",
  "selected_expert": "Expert_Epsilon_7432",
  "selection_reasoning": "Highest quality score (0.91): Synthesis: 0.38, Depth: 0.23, Innovation: 0.17, Clarity: 0.13",
  "quality_metrics": {
    "depth_score": 0.92,
    "innovation_score": 0.85,
    "synthesis_score": 0.95,
    "clarity_score": 0.91,
    "overall_quality": 0.91
  },
  "bias_elimination_report": {
    "anonymity_enforced": true,
    "model_identities_hidden": true,
    "quality_based_selection": true,
    "bias_free_process": true
  },
  "collaboration_timeline": [
    "🧠 Expert Alpha: Strategic analysis with anonymous thinking",
    "🔍 Expert Beta: Research synthesis building on Alpha",
    "🏗️ Expert Gamma: Solution design integrating previous insights",
    "🔍 Expert Delta: Critical review and improvements",
    "⚡ Generated 3 anonymous synthesis candidates",
    "🎯 Selected best synthesis based on quality metrics"
  ]
}
```

### **Enhanced Thinking Response:**
```json
{
  "final_report": "Comprehensive solution with transparent reasoning...",
  "collaboration_strategy": "enhanced",
  "thinking_journey": [
    "🧠 Strategic Analysis: Breaking down problem into core components",
    "🔍 Knowledge Synthesis: Current research shows best practices...",
    "🏗️ Solution Design: Integrating strategic + research insights...",
    "🔍 Critical Enhancement: Adding security and scalability...",
    "⚡ Team Synthesis: Weaving together all expert insights..."
  ],
  "collaboration_quality_score": 0.95,
  "key_insights": [
    {
      "agent_role": "strategic_analyst",
      "insight_type": "pattern", 
      "content": "The key challenge is operational transformation...",
      "confidence": 0.9
    }
  ]
}
```

---

## 🔧 **Implementation Steps**

### **Step 1: Update Imports**
```python
# In app/api/collaboration.py
from app.services.enhanced_main_assistant import enhanced_main_assistant, CollaborationStrategy
```

### **Step 2: Enhance Request Model**
```python
class CollaborationRequest(BaseModel):
    # ... existing fields ...
    collaboration_strategy: Optional[str] = None
    enable_anonymous: Optional[bool] = False
    show_thinking: Optional[bool] = False
```

### **Step 3: Update Collaborate Function**
```python
# Replace main_assistant.handle_message with enhanced_main_assistant.handle_message
result = await enhanced_main_assistant.handle_message(...)
```

### **Step 4: Update Response Format**
```python
return {
    "final_report": result["content"],
    "collaboration_strategy": result["collaboration_strategy"],
    # ... add enhanced fields ...
}
```

### **Step 5: Test Integration**
```bash
# Test different strategies
curl -X POST /collaborate -d '{"message": "Compare React vs Vue", "enable_anonymous": true}'
curl -X POST /collaborate -d '{"message": "Explain how GraphQL works", "show_thinking": true}' 
curl -X POST /collaborate -d '{"message": "Design scalable architecture", "collaboration_strategy": "nextgen"}'
```

---

## ✅ **Verification Checklist**

- [ ] **Enhanced imports added** to collaboration.py
- [ ] **Request model updated** with new parameters
- [ ] **Collaborate function modified** to use enhanced assistant
- [ ] **Response format updated** with enhanced fields
- [ ] **Backward compatibility maintained** for existing clients
- [ ] **Error handling updated** for new collaboration modes
- [ ] **Testing completed** for all collaboration strategies

---

## 🎉 **Result: Complete Integration**

After integration, your `/collaborate` endpoint will support:

### **✅ Anonymous Collaboration**
- Bias-free LLM collaboration
- Quality-based final selection
- Complete anonymity reports

### **✅ Enhanced Thinking**  
- Transparent reasoning processes
- Progressive knowledge building
- Collaborative intelligence tracking

### **✅ Next-Gen Swarming**
- Intelligent model coordination
- Adaptive task orchestration
- Performance optimization

### **✅ Backward Compatibility**
- Legacy sequential mode still available
- Existing API clients continue working
- Gradual migration support

**🚀 Your `/collaborate` function now powers the most advanced AI collaboration platform in existence!**