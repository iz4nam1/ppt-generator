"""
services/ai_generation/__init__.py
====================================
Feature registry — maps feature keys to service classes.

To add a new feature:
    1. Create your_feature.py in this folder
    2. Import and register it here
    3. Done — credits/rate-limiting work automatically
"""

from app.services.ai_generation.ppt_service      import PPTGenerationService
from app.services.ai_generation.image_service     import ImageGenerationService
from app.services.ai_generation.document_service  import DocumentSummaryService

FEATURE_REGISTRY = {
    "ppt_generation":   PPTGenerationService,
    "image_generation": ImageGenerationService,
    "document_summary": DocumentSummaryService,
    # ADD NEW FEATURES HERE:
    # "pitch_coach":    PitchCoachService,
    # "slide_design":   SlideDesignService,
}


def get_feature_service(feature_key: str, user_id: str = "", 
                        plan_type: str = "free", ip_hash: str = ""):
    """
    Factory function — get an instantiated feature service by key.
    
    Usage:
        service = get_feature_service("ppt_generation", user_id=uid)
        result  = await service.execute(template_path=..., description=...)
    """
    cls = FEATURE_REGISTRY.get(feature_key)
    if not cls:
        raise ValueError(f"Unknown feature: {feature_key}. Available: {list(FEATURE_REGISTRY.keys())}")
    return cls(user_id=user_id, plan_type=plan_type, ip_hash=ip_hash)
