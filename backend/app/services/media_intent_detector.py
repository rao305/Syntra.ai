"""Intent detection for image and graph generation requests."""
import logging
import re
from typing import Optional, Dict, Literal

logger = logging.getLogger(__name__)


MediaIntent = Literal["image", "graph", "none"]


class MediaIntentDetector:
    """Detects when user wants to generate images or graphs."""
    
    # Keywords that suggest image generation
    IMAGE_KEYWORDS = [
        "generate image", "create image", "draw", "picture", "photo", "illustration",
        "visualize", "show me an image", "make an image", "image of", "picture of",
        "dall-e", "dalle", "stable diffusion", "midjourney", "generate a picture"
    ]
    
    # Keywords that suggest graph generation
    GRAPH_KEYWORDS = [
        "graph", "chart", "plot", "visualize", "show data", "display data",
        "line chart", "bar chart", "pie chart", "scatter plot", "area chart",
        "plot the data", "create a graph", "make a chart", "draw a graph",
        "visualization", "matplotlib", "show trends", "plot over time"
    ]
    
    def detect_intent(self, message: str, previous_ai_message: Optional[str] = None) -> tuple[MediaIntent, Optional[Dict]]:
        """
        Detect if user wants to generate an image or graph.
        
        Args:
            message: User's message
            previous_ai_message: Optional previous AI message (for context when user says "just generate")
            
        Returns:
            Tuple of (intent_type, metadata_dict)
            intent_type: "image", "graph", or "none"
            metadata: Optional dict with extracted parameters
        """
        message_lower = message.lower().strip()
        
        # Check for standalone "generate" or "just generate" - use previous AI message as prompt
        if re.search(r'^(just\s+)?generate$|^(just\s+)?generate\s*$|^(nothing\s+as\s+such\s+)?just\s+generate', message_lower):
            if previous_ai_message:
                # User wants to generate based on previous AI description
                return ("image", {"prompt": previous_ai_message.strip(), "use_previous": True})
            else:
                # Fallback to generic prompt
                return ("image", {"prompt": "A beautiful illustration"})
        
        # Check for image generation intent - improved patterns
        # Pattern 1: "generate [to me] [an] image of X" or "generate [to me] image of X"
        if re.search(r'generate\s+(to\s+me\s+)?(an?\s+)?image\s+of', message_lower):
            return ("image", {"prompt": self._extract_image_prompt(message, previous_ai_message)})
        
        # Pattern 2: "generate [to me] [an] image" or "generate [to me] image"
        if re.search(r'generate\s+(to\s+me\s+)?(an?\s+)?image', message_lower):
            return ("image", {"prompt": self._extract_image_prompt(message, previous_ai_message)})
        
        # Pattern 3: "create [an] image of X" or "create image of X"
        if re.search(r'create\s+(an?\s+)?image\s+of', message_lower):
            return ("image", {"prompt": self._extract_image_prompt(message, previous_ai_message)})
        
        # Pattern 4: "image of X" or "picture of X"
        if re.search(r'(image|picture|photo)\s+of\s+', message_lower):
            return ("image", {"prompt": self._extract_image_prompt(message, previous_ai_message)})
        
        # Pattern 5: Other strong indicators
        if any(phrase in message_lower for phrase in ["generate image", "create image", "draw", "picture of", "image of"]):
            return ("image", {"prompt": self._extract_image_prompt(message, previous_ai_message)})
        
        # Check for graph generation
        if any(phrase in message_lower for phrase in ["graph", "chart", "plot", "visualize data", "show data"]):
            return ("graph", {"request": message})
        
        # Check for explicit commands with more flexible patterns
        if re.search(r'(generate|create|make|draw)\s+(to\s+me\s+)?(an?\s+)?(image|picture|photo)', message_lower):
            return ("image", {"prompt": self._extract_image_prompt(message, previous_ai_message)})
        
        if re.search(r'(generate|create|make|draw|plot)\s+(an?\s+)?(graph|chart)', message_lower):
            return ("graph", {"request": message})
        
        # Score-based detection as fallback
        image_score = sum(1 for keyword in self.IMAGE_KEYWORDS if keyword in message_lower)
        graph_score = sum(1 for keyword in self.GRAPH_KEYWORDS if keyword in message_lower)
        
        if image_score > graph_score and image_score > 0:
            return ("image", {"prompt": self._extract_image_prompt(message, previous_ai_message)})
        
        if graph_score > image_score and graph_score > 0:
            return ("graph", {"request": message})
        
        return ("none", None)
    
    def _extract_image_prompt(self, message: str, previous_ai_message: Optional[str] = None) -> str:
        """Extract the image generation prompt from the message."""
        message_lower = message.lower().strip()
        
        # If message is just "generate" or "just generate", use previous AI message
        if re.search(r'^(just\s+)?generate$|^(just\s+)?generate\s*$', message_lower):
            if previous_ai_message:
                return previous_ai_message.strip()
            return "A beautiful illustration"
        
        # Handle "generate to me an image of X" pattern
        message = re.sub(r'generate\s+(to\s+me\s+)?(an?\s+)?image\s+of\s+', '', message, flags=re.IGNORECASE)
        
        # Remove other common prefixes
        message = re.sub(r'^(generate|create|make|draw|show me)\s+(to\s+me\s+)?(an?\s+)?(image|picture|photo|illustration)\s+(of|for|showing)?\s*', '', message, flags=re.IGNORECASE)
        message = message.strip()
        
        # If message starts with quote, extract quoted text
        quote_match = re.search(r'["\']([^"\']+)["\']', message)
        if quote_match:
            return quote_match.group(1)
        
        # Return cleaned message
        return message if message else "A beautiful illustration"
    
    def should_generate_media(self, message: str) -> bool:
        """Quick check if media generation is needed."""
        intent, _ = self.detect_intent(message)
        return intent != "none"


# Global instance
media_intent_detector = MediaIntentDetector()

