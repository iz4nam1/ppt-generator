"""
services/rate_limit.py
======================
Per-user rate limiting layer.

CURRENT STATE:
  - Logs all usage to usage_log table
  - check_rate_limit() always returns allowed=True
  - Daily limit check is ACTIVE (prevents abuse even now)

HOW TO ACTIVATE FULL ENFORCEMENT:
  1. Set RATE_LIMITS_ENFORCED = True
  2. Limits per plan are in config.DAILY_LIMITS
  3. No route changes needed — routes already call check_rate_limit()

FUTURE:
  - Redis-backed sliding window for real-time per-minute limits
  - Replace sqlite usage_log with Redis INCR + TTL for performance
"""

import logging
import uuid
from datetime import datetime
from app.database import get_db
from app.config import DAILY_LIMITS

log = logging.getLogger(__name__)

# ── Master switch ──────────────────────────────────────────────────────────────
RATE_LIMITS_ENFORCED = True   # Daily limit is ON — prevents free tier abuse


class RateLimitExceededError(Exception):
    pass


def log_usage(user_id: str, feature: str, ip_hash: str = ""):
    """
    Record every AI feature use in usage_log.
    Even when limits aren't enforced, we log — gives us data.

    FUTURE: Replace with Redis INCR for high-throughput tracking.
    """
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO usage_log (id, user_id, feature, ip_hash, created_at) VALUES (?,?,?,?,?)",
                (uuid.uuid4().hex, user_id or None, feature,
                 ip_hash, datetime.utcnow().isoformat())
            )
    except Exception as e:
        log.warning(f"Usage log write failed (non-fatal): {e}")


def check_rate_limit(user_id: str, feature: str, plan_type: str = "free") -> dict:
    """
    Check if user is within rate limits for a feature.

    CURRENT:  Enforces daily limits only.
    FUTURE:   Add per-minute sliding window when on Redis.

    Args:
        user_id:   User ID (empty string for anonymous)
        feature:   Feature key (e.g. 'ppt_generation')
        plan_type: User's plan ('free' | 'student' | 'pro')

    Returns:
        dict: {"allowed": bool, "reason": str, "remaining_today": int}

    Raises:
        RateLimitExceededError: When limit is hit
    """
    if not user_id:
        # Anonymous users: very limited
        # FUTURE: track by IP hash instead
        return {"allowed": True, "reason": "anonymous", "remaining_today": -1}

    daily_limit = DAILY_LIMITS.get(plan_type, DAILY_LIMITS["free"])
    today       = datetime.utcnow().strftime("%Y-%m-%d")

    with get_db() as conn:
        row = conn.execute(
            """SELECT COUNT(*) as c FROM usage_log
               WHERE user_id=? AND feature=? AND created_at LIKE ?""",
            (user_id, feature, f"{today}%")
        ).fetchone()

    used_today = row["c"] if row else 0
    remaining  = daily_limit - used_today

    if RATE_LIMITS_ENFORCED and remaining <= 0:
        log.info(f"Rate limit hit: {user_id} / {feature} / {plan_type}")
        raise RateLimitExceededError(
            f"Daily limit reached ({daily_limit}/day on {plan_type} plan). "
            f"Try again tomorrow or upgrade your plan."
        )

    return {
        "allowed":         True,
        "remaining_today": remaining,
        "daily_limit":     daily_limit,
        "plan_type":       plan_type,
    }


def get_usage_stats(user_id: str) -> dict:
    """
    Get usage stats for a user.
    FUTURE: Expose via GET /me/usage endpoint.
    """
    today = datetime.utcnow().strftime("%Y-%m-%d")

    with get_db() as conn:
        today_count = conn.execute(
            "SELECT COUNT(*) as c FROM usage_log WHERE user_id=? AND created_at LIKE ?",
            (user_id, f"{today}%")
        ).fetchone()["c"]

        total_count = conn.execute(
            "SELECT COUNT(*) as c FROM usage_log WHERE user_id=?",
            (user_id,)
        ).fetchone()["c"]

        by_feature = conn.execute(
            "SELECT feature, COUNT(*) as c FROM usage_log WHERE user_id=? GROUP BY feature",
            (user_id,)
        ).fetchall()

    return {
        "today":      today_count,
        "total":      total_count,
        "by_feature": {row["feature"]: row["c"] for row in by_feature},
    }
