"""
services/ai_generation/image_service.py
=========================================
Image generation feature — PLACEHOLDER.

CURRENT STATE:  Not implemented. Returns placeholder response.

HOW TO IMPLEMENT:
    Option A — Stability AI:
        pip install stability-sdk
        Use api.stability.ai to generate from text prompt

    Option B — Replicate:
        pip install replicate
        Run SDXL or Flux models via API

    Option C — Fal.ai:
        pip install fal-client
        Fast, cheap inference for image models

WIRING CHECKLIST:
    [ ] Add STABILITY_API_KEY or REPLICATE_API_TOKEN to config.py
    [ ] Add "image_generation": 5 to config.CREDIT_COSTS (already there)
    [ ] Implement run() below
    [ ] Add POST /generate/image route in routes/generate.py
    [ ] Add image_service to __init__.py registry
"""

import logging
from app.services.ai_generation.base import AIFeature

log = logging.getLogger(__name__)


class ImageGenerationService(AIFeature):
    """
    AI image generation feature.
    Credits and rate limiting handled by AIFeature base class.
    """
    FEATURE_KEY = "image_generation"

    async def run(self, prompt: str, style: str = "photorealistic", **kwargs):
        """
        Generate an image from a text prompt.

        Args:
            prompt: Text description of the image
            style:  'photorealistic' | 'illustration' | 'diagram'

        Returns:
            dict with image_url or image_bytes

        TODO: Implement with chosen provider (see module docstring)
        """
        log.info(f"[PLACEHOLDER] Image generation requested: {prompt[:50]}")

        # TODO: Replace with real implementation
        # Example with Replicate:
        # import replicate
        # output = replicate.run(
        #     "black-forest-labs/flux-schnell",
        #     input={"prompt": prompt}
        # )
        # return {"image_url": output[0], "prompt": prompt}

        return {
            "success": False,
            "message": "Image generation coming soon.",
            "feature": self.FEATURE_KEY,
        }
