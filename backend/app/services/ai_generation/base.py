"""
services/ai_generation/base.py
================================
Base class for all AI generation features.

Every AI feature (PPT, image, document summary, etc.) inherits from AIFeature.
This ensures:
  - Consistent credit checking before generation
  - Consistent usage logging after generation
  - Consistent error handling
  - Easy addition of new features

HOW TO ADD A NEW AI FEATURE:
    1. Create services/ai_generation/your_feature.py
    2. class YourFeature(AIFeature):
           FEATURE_KEY = "your_feature"
           async def run(self, **kwargs): ...
    3. Register in services/ai_generation/__init__.py
    4. Add a route in routes/generate.py
    5. Add credit cost in config.CREDIT_COSTS
    Done — credits, rate limiting, logging all work automatically.
"""

import logging
from abc import ABC, abstractmethod
from app.services.credits import check_user_credits, deduct_credits
from app.services.rate_limit import check_rate_limit, log_usage

log = logging.getLogger(__name__)


class AIFeature(ABC):
    """
    Abstract base class for all AI generation features.

    Subclasses must:
        - Set FEATURE_KEY (matches config.CREDIT_COSTS key)
        - Implement run(**kwargs) → result

    The base class handles:
        - Credit check before run
        - Rate limit check before run
        - Usage logging after run
        - Credit deduction after successful run
    """

    FEATURE_KEY: str = "unknown"

    def __init__(self, user_id: str = "", plan_type: str = "free", ip_hash: str = ""):
        self.user_id   = user_id
        self.plan_type = plan_type
        self.ip_hash   = ip_hash

    def pre_run_checks(self):
        """
        Run all checks before executing the AI feature.
        Raises an exception if any check fails.
        Called automatically by execute().
        """
        # 1. Rate limit check
        check_rate_limit(self.user_id, self.FEATURE_KEY, self.plan_type)

        # 2. Credit check
        check_user_credits(self.user_id, self.FEATURE_KEY)

    def post_run_actions(self):
        """
        Run cleanup/accounting after successful AI generation.
        Called automatically by execute().
        """
        # 1. Log usage (always)
        log_usage(self.user_id, self.FEATURE_KEY, self.ip_hash)

        # 2. Deduct credits (no-op until CREDITS_ENFORCED=True)
        deduct_credits(self.user_id, self.FEATURE_KEY)

    async def execute(self, **kwargs):
        """
        Main entry point. Runs checks → feature → post-actions.
        Routes should call this, not run() directly.
        """
        self.pre_run_checks()
        result = await self.run(**kwargs)
        self.post_run_actions()
        return result

    @abstractmethod
    async def run(self, **kwargs):
        """
        Implement the actual AI generation logic here.
        Called by execute() after all checks pass.
        """
        raise NotImplementedError
