"""
Image Analysis Service

Analyzes images to determine content type and routes to the best AI model.
Uses a fast vision model (Gemini Flash) to analyze the image, then routes
to the most appropriate specialist model based on the content.
"""

import logging
from typing import Dict, Optional, List, Any
from app.models.provider_key import ProviderType
from app.services.provider_dispatch import call_provider_adapter

logger = logging.getLogger(__name__)


async def analyze_image_and_route(
    image_data: str,  # Base64 encoded image
    user_query: Optional[str] = None,
    api_keys: Dict[str, str] = None
) -> Dict[str, Any]:
    """
    Analyze an image and determine the best AI model to handle it.
    
    Args:
        image_data: Base64 encoded image data
        user_query: Optional user query about the image
        api_keys: Dictionary of API keys by provider
        
    Returns:
        Dict with:
            - provider: ProviderType enum
            - model: Model name string
            - reason: Routing reason
            - image_type: Detected image type (code, diagram, photo, document, etc.)
            - analysis: Brief analysis of the image content
    """
    
    if not api_keys:
        api_keys = {}
    
    # Use Gemini Flash for fast image analysis (it's fast and good at vision)
    gemini_key = api_keys.get("gemini") or api_keys.get("google")
    
    if not gemini_key:
        # Fallback: if no Gemini key, default to Gemini anyway (will fail gracefully)
        logger.warning("No Gemini API key available for image analysis, using default routing")
        return {
            "provider": ProviderType.GEMINI,
            "model": "gemini-1.5-flash",  # More stable than 2.5-flash
            "reason": "Image analysis - defaulting to Gemini (no API key for analysis)",
            "image_type": "unknown",
            "analysis": "Unable to analyze image - no API key"
        }
    
    try:
        # Quick analysis prompt - fast and focused
        analysis_prompt = """Analyze this image and provide a brief analysis in JSON format:
{
  "image_type": "code_screenshot" | "diagram" | "photo" | "document" | "chart" | "ui_screenshot" | "other",
  "content_summary": "Brief 1-2 sentence description",
  "best_model_type": "vision" | "code" | "general" | "analysis" | "creative",
  "requires_specialist": true | false
}

Focus on:
- If it's code/screenshots → code specialist
- If it's diagrams/charts → analysis specialist  
- If it's photos → general vision
- If it's documents → document analysis specialist

Respond ONLY with valid JSON, no other text."""

        # Build messages with image - use standard format (adapter will convert)
        # Extract base64 data if it's a data URL
        base64_data = image_data
        if image_data.startswith("data:"):
            # Extract base64 part from data URL
            base64_data = image_data.split(",")[1] if "," in image_data else image_data
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": analysis_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_data}"
                        }
                    }
                ]
            }
        ]
        
        # Call Gemini Flash for fast analysis - use stable model
        response = await call_provider_adapter(
            provider=ProviderType.GEMINI,
            model="gemini-1.5-flash",  # More stable than 2.5-flash
            messages=messages,
            api_key=gemini_key,
            temperature=0.1,  # Low temperature for consistent analysis
            max_tokens=200  # Short response
        )
        
        if not response or not hasattr(response, 'content'):
            raise ValueError("No response from image analysis")
        
        analysis_text = response.content.strip() if response.content else ""
        
        if not analysis_text:
            raise ValueError("Empty response from image analysis")
        
        # Parse JSON from response (handle markdown code blocks if present)
        import json
        import re
        
        # Extract JSON from markdown code blocks if present
        json_match = re.search(r'\{[^}]+\}', analysis_text, re.DOTALL)
        if json_match:
            analysis_text = json_match.group(0)
        else:
            # If no JSON found, log the actual response for debugging
            logger.warning(f"Image analysis response doesn't contain JSON. Response: {analysis_text[:200]}")
            raise ValueError(f"Invalid JSON response from image analysis: {analysis_text[:200]}")
        
        try:
            analysis_data = json.loads(analysis_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from image analysis. Response: {analysis_text[:200]}, Error: {e}")
            raise ValueError(f"Failed to parse JSON from image analysis: {str(e)}")
        
        image_type = analysis_data.get("image_type", "other")
        best_model_type = analysis_data.get("best_model_type", "vision")
        requires_specialist = analysis_data.get("requires_specialist", False)
        content_summary = analysis_data.get("content_summary", "")
        
        # Route to best model based on analysis
        provider, model, reason = _route_based_on_analysis(
            image_type=image_type,
            best_model_type=best_model_type,
            requires_specialist=requires_specialist,
            user_query=user_query,
            content_summary=content_summary
        )
        
        return {
            "provider": provider,
            "model": model,
            "reason": reason,
            "image_type": image_type,
            "analysis": content_summary
        }
        
    except Exception as e:
        logger.error(f"Image analysis failed: {e}", exc_info=True)
        # Fallback to Gemini Flash for vision - use stable model
        return {
            "provider": ProviderType.GEMINI,
            "model": "gemini-1.5-flash",  # More stable than 2.5-flash
            "reason": f"Image analysis failed, defaulting to Gemini Flash: {str(e)}",
            "image_type": "unknown",
            "analysis": f"Analysis error: {str(e)}"
        }


def _route_based_on_analysis(
    image_type: str,
    best_model_type: str,
    requires_specialist: bool,
    user_query: Optional[str] = None,
    content_summary: str = ""
) -> tuple[ProviderType, str, str]:
    """
    Route to the best model based on image analysis.
    
    Returns:
        (provider, model, reason) tuple
    """
    
    query_lower = (user_query or "").lower()
    
    # Code screenshots → GPT-4o (best code understanding)
    if image_type == "code_screenshot" or "code" in best_model_type.lower():
        return (
            ProviderType.OPENAI,
            "gpt-4o",
            f"Code screenshot detected - using GPT-4o for code analysis"
        )
    
    # UI screenshots → GPT-4o (good at UI/UX analysis)
    if image_type == "ui_screenshot":
        return (
            ProviderType.OPENAI,
            "gpt-4o",
            f"UI screenshot detected - using GPT-4o for UI analysis"
        )
    
    # Diagrams and charts → Gemini Flash (good at analysis)
    if image_type in ["diagram", "chart"] or "analysis" in best_model_type.lower():
        return (
            ProviderType.GEMINI,
            "gemini-1.5-flash",  # More stable than 2.5-flash
            f"{image_type.title()} detected - using Gemini for analysis"
        )
    
    # Documents → GPT-4o (best at document understanding)
    if image_type == "document":
        return (
            ProviderType.OPENAI,
            "gpt-4o",
            "Document detected - using GPT-4o for document analysis"
        )
    
    # Photos with specific queries → route based on query
    if image_type == "photo":
        if any(word in query_lower for word in ["code", "programming", "syntax", "error"]):
            return (
                ProviderType.OPENAI,
                "gpt-4o",
                "Photo with code-related query - using GPT-4o"
            )
        elif any(word in query_lower for word in ["analyze", "explain", "what", "describe"]):
            return (
                ProviderType.GEMINI,
                "gemini-1.5-flash",  # More stable than 2.5-flash
                "Photo analysis query - using Gemini Flash"
            )
        else:
            # Default for photos
            return (
                ProviderType.GEMINI,
                "gemini-1.5-flash",  # More stable than 2.5-flash
                "Photo detected - using Gemini Flash for vision"
            )
    
    # Default: Gemini Flash (fast and good at vision)
    return (
        ProviderType.GEMINI,
        "gemini-1.5-flash-002",  # More stable than 2.5-flash
        f"Image detected ({image_type}) - using Gemini Flash for vision analysis"
    )


