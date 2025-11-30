"""Image generation service supporting multiple LLM and image providers."""
import logging
from typing import List, Optional
import aiohttp
import json

from app.services.collaborate.models import ImageSpec, GeneratedImage, ImagePurpose
from app.models.provider_key import ProviderType

logger = logging.getLogger(__name__)


class ImageGenerationService:
    """Service for generating images from text prompts using various providers."""

    def __init__(self):
        """Initialize the service."""
        self.providers = {
            'openai': self._generate_openai,
            'replicate': self._generate_replicate,
            'huggingface': self._generate_huggingface,
        }

    async def generate_image(
        self,
        spec: ImageSpec,
        provider: str = 'openai',
        api_key: str = None,
    ) -> Optional[GeneratedImage]:
        """
        Generate a single image from a spec.

        Args:
            spec: ImageSpec with prompt and parameters
            provider: Image provider to use (openai, replicate, huggingface)
            api_key: API key for the provider

        Returns:
            GeneratedImage with URL, or None if generation fails
        """
        if not api_key:
            logger.warning(f"No API key provided for image provider {provider}")
            return None

        generator = self.providers.get(provider)
        if not generator:
            logger.warning(f"Unknown image provider: {provider}")
            return None

        try:
            url = await generator(spec, api_key)
            if url:
                return GeneratedImage(
                    id=spec.id,
                    url=url,
                    purpose=spec.purpose,
                    alt=spec.prompt[:100],
                    mime_type="image/png",
                )
        except Exception as e:
            logger.error(f"Failed to generate image {spec.id}: {str(e)}")

        return None

    async def _generate_openai(self, spec: ImageSpec, api_key: str) -> Optional[str]:
        """Generate image using OpenAI DALL-E."""
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=api_key)

            # Build size from aspect ratio
            size_map = {
                "1:1": "1024x1024",
                "16:9": "1792x1024",
                "4:3": "1280x960",
                "3:2": "1440x960",
            }
            size = size_map.get(spec.aspect_ratio or "1:1", "1024x1024")

            response = await client.images.generate(
                model="dall-e-3",
                prompt=spec.prompt,
                size=size,
                quality="standard",
                n=1,
            )

            if response.data and len(response.data) > 0:
                return response.data[0].url

        except Exception as e:
            logger.error(f"OpenAI image generation failed: {str(e)}")

        return None

    async def _generate_replicate(
        self,
        spec: ImageSpec,
        api_key: str,
    ) -> Optional[str]:
        """Generate image using Replicate (Stable Diffusion)."""
        try:
            import replicate

            # Set API token
            replicate.Client(api_token=api_key)

            # Use Stable Diffusion 3
            output = await replicate.async_run(
                "stability-ai/stable-diffusion-3",
                input={
                    "prompt": spec.prompt,
                    "aspect_ratio": spec.aspect_ratio or "1:1",
                    "output_format": "png",
                },
            )

            if output and isinstance(output, list) and len(output) > 0:
                return output[0]

        except Exception as e:
            logger.error(f"Replicate image generation failed: {str(e)}")

        return None

    async def _generate_huggingface(
        self,
        spec: ImageSpec,
        api_key: str,
    ) -> Optional[str]:
        """Generate image using Hugging Face Diffusers API."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }

                payload = {
                    "inputs": spec.prompt,
                }

                # Use Stable Diffusion model
                model_id = "stabilityai/stable-diffusion-2"

                async with session.post(
                    f"https://api-inference.huggingface.co/models/{model_id}",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status == 200:
                        image_bytes = await resp.read()
                        # Return as data URI for simplicity
                        import base64

                        b64_str = base64.b64encode(image_bytes).decode('utf-8')
                        return f"data:image/png;base64,{b64_str}"

        except Exception as e:
            logger.error(f"Hugging Face image generation failed: {str(e)}")

        return None


async def generate_images(
    specs: List[ImageSpec],
    provider: str = 'openai',
    api_key: str = None,
) -> List[GeneratedImage]:
    """
    Generate multiple images from specs.

    Args:
        specs: List of ImageSpec objects
        provider: Image provider to use
        api_key: API key for the provider

    Returns:
        List of GeneratedImage objects (may contain fewer if some failed)
    """
    service = ImageGenerationService()
    images = []

    for spec in specs:
        try:
            image = await service.generate_image(spec, provider, api_key)
            if image:
                images.append(image)
        except Exception as e:
            logger.error(f"Failed to generate image {spec.id}: {str(e)}")
            continue

    return images


# Convenience function to select best image provider from available API keys
def select_image_provider(api_keys: dict) -> tuple[str, Optional[str]]:
    """
    Select the best available image provider based on api_keys.

    Args:
        api_keys: Dict of provider -> api_key

    Returns:
        Tuple of (provider_name, api_key) or (None, None) if no provider available
    """
    # Priority order
    priority = ['openai', 'replicate', 'huggingface']

    for provider in priority:
        if api_keys.get(provider):
            return provider, api_keys[provider]

    # Fallback: try to use any available key
    if api_keys.get('openai'):
        return 'openai', api_keys['openai']

    return None, None
