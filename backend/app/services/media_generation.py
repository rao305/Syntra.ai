"""Media generation service for images and graphs."""
import logging
import io
import base64
import uuid
from typing import Optional, Dict, Any, List
import re

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

from app.services.collaborate.image_generation_service import ImageGenerationService, select_image_provider
from app.services.collaborate.models import ImageSpec, GeneratedImage, ImagePurpose

logger = logging.getLogger(__name__)


class MediaGenerationService:
    """Service for generating images and graphs from user requests."""
    
    def __init__(self):
        self.image_service = ImageGenerationService()
    
    async def generate_image_from_prompt(
        self,
        prompt: str,
        api_keys: Dict[str, str]
    ) -> Optional[GeneratedImage]:
        """
        Generate an image from a text prompt using DALL-E or other providers.
        
        Args:
            prompt: Text description of the image to generate
            api_keys: Dictionary of provider -> api_key
            
        Returns:
            GeneratedImage with URL or base64 data, or None if generation fails
        """
        try:
            # Select best available image provider
            provider, api_key = select_image_provider(api_keys)
            if not provider or not api_key:
                logger.warning(f"No image generation provider available. Available keys: {list(api_keys.keys())}")
                return None
            
            logger.info(f"Using image provider: {provider}")
            
            # Create image spec
            spec = ImageSpec(
                id=str(uuid.uuid4()),
                purpose="illustration",
                prompt=prompt,
                aspect_ratio="1:1"
            )
            
            # Generate image with fallback logic
            logger.info(f"Generating image with provider {provider} for prompt: {prompt[:100]}")
            image = await self.image_service.generate_image(spec, provider, api_key)
            
            # If Gemini fails, try OpenAI as fallback
            if not image and provider in ['gemini', 'google'] and api_keys.get('openai'):
                logger.info(f"Gemini/Imagen failed, falling back to OpenAI DALL-E")
                provider = 'openai'
                api_key = api_keys['openai']
                image = await self.image_service.generate_image(spec, provider, api_key)
            
            if image:
                logger.info(f"Image generated successfully with {provider}: {image.url[:100] if len(image.url) > 100 else image.url}")
            else:
                logger.warning(f"Image generation failed for all providers. Tried: {provider}")
            
            return image
            
        except Exception as e:
            logger.error(f"Failed to generate image: {str(e)}")
            return None
    
    async def generate_graph_from_request(
        self,
        request: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Generate a matplotlib graph from a user request.
        
        Args:
            request: User's request describing the graph (e.g., "plot sales over time")
            data: Optional structured data. If None, will try to extract from request or generate sample data
            
        Returns:
            Base64-encoded PNG image as data URI, or None if generation fails
        """
        try:
            # Parse request to determine graph type and extract data
            graph_type, labels, series_data, title, x_label, y_label = self._parse_graph_request(request, data)
            
            if not labels or not series_data:
                logger.warning("Could not extract sufficient data for graph")
                return None
            
            # Create figure
            fig, ax = plt.subplots(figsize=(12, 6))
            fig.patch.set_facecolor('#1a1a1a')
            ax.set_facecolor('#0f0f0f')
            
            # Set text colors for dark theme
            ax.tick_params(colors='#e8eaed')
            ax.spines['bottom'].set_color('#3a3a3a')
            ax.spines['top'].set_color('#3a3a3a')
            ax.spines['right'].set_color('#3a3a3a')
            ax.spines['left'].set_color('#3a3a3a')
            
            # Render based on graph type
            if graph_type == "line":
                self._render_line_chart(ax, labels, series_data)
            elif graph_type == "bar":
                self._render_bar_chart(ax, labels, series_data)
            elif graph_type == "pie":
                self._render_pie_chart(fig, labels, series_data)
            elif graph_type == "scatter":
                self._render_scatter_chart(ax, labels, series_data)
            elif graph_type == "area":
                self._render_area_chart(ax, labels, series_data)
            else:
                # Default to line chart
                self._render_line_chart(ax, labels, series_data)
            
            # Set labels and title
            if title:
                ax.set_title(title, fontsize=14, fontweight='bold', pad=20, color='#e8eaed')
            if x_label:
                ax.set_xlabel(x_label, fontsize=11, color='#e8eaed')
            if y_label:
                ax.set_ylabel(y_label, fontsize=11, color='#e8eaed')
            
            # Add legend if multiple series
            if len(series_data) > 1 and graph_type != "pie":
                ax.legend(loc='upper left', framealpha=0.9, facecolor='#1a1a1a', edgecolor='#3a3a3a', labelcolor='#e8eaed')
            
            # Format grid
            ax.grid(True, alpha=0.2, linestyle='--', linewidth=0.5, color='#3a3a3a')
            
            # Tight layout
            plt.tight_layout()
            
            # Render to PNG bytes
            img_bytes = io.BytesIO()
            fig.savefig(img_bytes, format='png', dpi=100, bbox_inches='tight', facecolor='#1a1a1a')
            img_bytes.seek(0)
            plt.close(fig)
            
            # Encode as base64 data URI
            b64_str = base64.b64encode(img_bytes.read()).decode('utf-8')
            data_uri = f"data:image/png;base64,{b64_str}"
            
            return data_uri
            
        except Exception as e:
            logger.error(f"Failed to generate graph: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _parse_graph_request(self, request: str, data: Optional[Dict[str, Any]] = None) -> tuple:
        """
        Parse user request to extract graph parameters.
        
        Returns:
            (graph_type, labels, series_data, title, x_label, y_label)
        """
        request_lower = request.lower()
        
        # Determine graph type
        graph_type = "line"  # default
        if any(word in request_lower for word in ["bar chart", "bar graph", "bars"]):
            graph_type = "bar"
        elif any(word in request_lower for word in ["pie chart", "pie graph"]):
            graph_type = "pie"
        elif any(word in request_lower for word in ["scatter plot", "scatter"]):
            graph_type = "scatter"
        elif any(word in request_lower for word in ["area chart", "area graph"]):
            graph_type = "area"
        elif any(word in request_lower for word in ["line chart", "line graph", "plot", "graph"]):
            graph_type = "line"
        
        # Extract title
        title = None
        title_match = re.search(r'(?:title|named|called)\s+["\']([^"\']+)["\']', request_lower)
        if title_match:
            title = title_match.group(1)
        elif "show" in request_lower or "display" in request_lower:
            # Try to extract what to show
            parts = request_lower.split("show")[-1].split("display")[-1].strip()
            if len(parts) < 50:
                title = parts.capitalize()
        
        # Extract axis labels
        x_label = None
        y_label = None
        x_match = re.search(r'x[-\s]?axis[:\s]+["\']?([^"\']+)["\']?', request_lower)
        if x_match:
            x_label = x_match.group(1)
        y_match = re.search(r'y[-\s]?axis[:\s]+["\']?([^"\']+)["\']?', request_lower)
        if y_match:
            y_label = y_match.group(1)
        
        # Use provided data if available
        if data:
            labels = data.get("labels", [])
            series = data.get("series", [])
            if labels and series:
                return (graph_type, labels, series, title, x_label, y_label)
        
        # Try to extract data from request text
        # Look for patterns like "2020: 100, 2021: 150" or "Q1: 50, Q2: 75"
        data_pattern = r'(\w+(?:\s+\d+)?)[:\s]+(\d+(?:\.\d+)?)'
        matches = re.findall(data_pattern, request)
        
        if matches:
            labels = [m[0] for m in matches]
            values = [float(m[1]) for m in matches]
            series_data = [{"name": "Data", "values": values}]
            return (graph_type, labels, series_data, title, x_label, y_label)
        
        # Generate sample data if nothing found
        # This is a fallback - in production, you'd want the LLM to extract or provide data
        labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
        values = [100, 120, 110, 140, 130, 150]
        series_data = [{"name": "Sample Data", "values": values}]
        
        return (graph_type, labels, series_data, title, x_label, y_label)
    
    def _render_line_chart(self, ax, labels: List[str], series_data: List[Dict]):
        """Render a line chart."""
        colors = ['#4285f4', '#ea4335', '#fbbc04', '#34a853', '#ff6d01', '#9c27b0']
        for idx, series in enumerate(series_data):
            ax.plot(
                range(len(labels)),
                series["values"],
                marker='o',
                label=series.get("name", f"Series {idx+1}"),
                linewidth=2.5,
                markersize=6,
                color=colors[idx % len(colors)],
            )
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45 if len(labels) > 5 else 0, color='#e8eaed')
    
    def _render_bar_chart(self, ax, labels: List[str], series_data: List[Dict]):
        """Render a bar chart."""
        colors = ['#4285f4', '#ea4335', '#fbbc04', '#34a853', '#ff6d01', '#9c27b0']
        x = range(len(labels))
        bar_width = 0.8 / len(series_data) if len(series_data) > 1 else 0.6
        
        for idx, series in enumerate(series_data):
            offset = (idx - len(series_data) / 2 + 0.5) * bar_width if len(series_data) > 1 else 0
            ax.bar(
                [i + offset for i in x],
                series["values"],
                bar_width,
                label=series.get("name", f"Series {idx+1}"),
                color=colors[idx % len(colors)],
                alpha=0.85,
            )
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45 if len(labels) > 5 else 0, color='#e8eaed')
    
    def _render_pie_chart(self, fig, labels: List[str], series_data: List[Dict]):
        """Render a pie chart."""
        ax = fig.add_subplot(111)
        values = series_data[0]["values"] if series_data else []
        colors = ['#4285f4', '#ea4335', '#fbbc04', '#34a853', '#ff6d01', '#9c27b0', '#00bcd4', '#ff9800']
        
        wedges, texts, autotexts = ax.pie(
            values,
            labels=labels,
            colors=colors[:len(labels)],
            autopct='%1.1f%%',
            startangle=90,
            textprops={'color': '#e8eaed'}
        )
        
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(10)
        
        ax.axis('equal')
    
    def _render_scatter_chart(self, ax, labels: List[str], series_data: List[Dict]):
        """Render a scatter chart."""
        colors = ['#4285f4', '#ea4335', '#fbbc04', '#34a853', '#ff6d01', '#9c27b0']
        x = range(len(labels))
        
        for idx, series in enumerate(series_data):
            ax.scatter(
                x,
                series["values"],
                s=100,
                label=series.get("name", f"Series {idx+1}"),
                color=colors[idx % len(colors)],
                alpha=0.7,
            )
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45 if len(labels) > 5 else 0, color='#e8eaed')
    
    def _render_area_chart(self, ax, labels: List[str], series_data: List[Dict]):
        """Render an area chart."""
        colors = ['#4285f4', '#ea4335', '#fbbc04', '#34a853', '#ff6d01', '#9c27b0']
        x = range(len(labels))
        
        for idx, series in enumerate(series_data):
            ax.fill_between(
                x,
                series["values"],
                alpha=0.6,
                label=series.get("name", f"Series {idx+1}"),
                color=colors[idx % len(colors)],
            )
        
        # Overlay lines for clarity
        for idx, series in enumerate(series_data):
            ax.plot(
                x,
                series["values"],
                linewidth=2,
                color=colors[idx % len(colors)],
            )
        
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45 if len(labels) > 5 else 0, color='#e8eaed')


# Global instance
media_generation_service = MediaGenerationService()

