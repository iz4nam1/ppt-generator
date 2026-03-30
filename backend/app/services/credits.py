"""
services/credits.py
===================
Credit management service.

CURRENT STATE:  Functions exist and are CALLED in routes, but credits
                are not actually enforced yet (check always passes).

HOW TO ACTIVATE: 
  1. Add card to Groq / set up payment gateway
  2. Flip CREDITS_ENFORCED = True below
  3. Wire process_payment() in payment_service.py to call add_credits()
  4. That's it — no route changes needed

Credit costs per feature are defined in config.py CREDIT_COSTS.
"""

import logging
import uuid
from datetime import datetime
from app.database import get_db
from app.config import CREDIT_COSTS, DEFAULT_CREDITS

log = logging.getLogger(__name__)

# ── Master switch ──────────────────────────────────────────────────────────────
# Flip to True when payment system is live and credits should be enforced
CREDITS_ENFORCED = False


class InsufficientCreditsError(Exception):
    """Raised when user doesn't have enough credits for an action."""
    pass


def check_user_credits(user_id: str, feature: str) -> bool:
    """
    Check if user has enough credits to use a feature.

    CURRENT:  Always returns True (not enforced)
    FUTURE:   Returns False if credits < CREDIT_COSTS[feature]

    Args:
        user_id: The user's ID
        feature: Feature key from config.CREDIT_COSTS (e.g. 'ppt_generation')

    Returns:
        True if user can proceed, False if insufficient credits

    Raises:
        InsufficientCreditsError: When CREDITS_ENFORCED=True and credits insufficient
    """
    if not CREDITS_ENFORCED:
        log.debug(f"Credits not enforced — allowing {user_id} to use {feature}")
        return True

    if not user_id:
        # Anonymous users: allow with no credit tracking
        return True

    cost = CREDIT_COSTS.get(feature, 0)
    if cost == 0:
        return True

    with get_db() as conn:
        row = conn.execute(
            "SELECT credits, plan_type FROM users WHERE id=?", (user_id,)
        ).fetchone()

    if not row:
        log.warning(f"check_user_credits: user {user_id} not found")
        return True  # Unknown user — allow but don't track

    if row["credits"] < cost:
        log.info(f"User {user_id} has {row['credits']} credits, needs {cost} for {feature}")
        raise InsufficientCreditsError(
            f"Not enough credits. This action costs {cost} credits. "
            f"You have {row['credits']}. Top up to continue."
        )

    return True


def deduct_credits(user_id: str, feature: str) -> int:
    """
    Deduct credits after a successful AI generation.

    CURRENT:  Logs the intent but does NOT deduct (not enforced)
    FUTURE:   Actually deducts from DB when CREDITS_ENFORCED=True

    Returns:
        Remaining credits after deduction (or current credits if not enforced)
    """
    cost = CREDIT_COSTS.get(feature, 0)

    if not CREDITS_ENFORCED or not user_id or cost == 0:
        log.debug(f"Would deduct {cost} credits from {user_id} for {feature} (not enforced)")
        return -1  # -1 signals "not enforced"

    with get_db() as conn:
        conn.execute(
            "UPDATE users SET credits = credits - ? WHERE id = ? AND credits >= ?",
            (cost, user_id, cost)
        )
        row = conn.execute(
            "SELECT credits FROM users WHERE id=?", (user_id,)
        ).fetchone()

    remaining = row["credits"] if row else 0
    log.info(f"Deducted {cost} credits from {user_id} for {feature}. Remaining: {remaining}")
    return remaining


def add_credits(user_id: str, amount: int, reason: str = "purchase") -> int:
    """
    Add credits to a user's account.
    Called by payment_service.py after successful payment.

    Args:
        user_id: Target user
        amount:  Number of credits to add
        reason:  'purchase' | 'student_bonus' | 'admin_grant' | 'referral'

    Returns:
        New total credits
    """
    if not user_id:
        log.warning("add_credits called with no user_id")
        return 0

    with get_db() as conn:
        conn.execute(
            "UPDATE users SET credits = credits + ? WHERE id = ?",
            (amount, user_id)
        )
        row = conn.execute(
            "SELECT credits FROM users WHERE id=?", (user_id,)
        ).fetchone()

    new_total = row["credits"] if row else 0
    log.info(f"Added {amount} credits to {user_id} (reason: {reason}). New total: {new_total}")
    return new_total


def get_user_credits(user_id: str) -> dict:
    """
    Get current credit balance and plan info for a user.

    FUTURE: Expose this via GET /me/credits endpoint.
    """
    if not user_id:
        return {"credits": 0, "plan_type": "anonymous"}

    with get_db() as conn:
        row = conn.execute(
            "SELECT credits, plan_type FROM users WHERE id=?", (user_id,)
        ).fetchone()

    if not row:
        return {"credits": 0, "plan_type": "unknown"}

    return {"credits": row["credits"], "plan_type": row["plan_type"]}


def grant_student_bonus(user_id: str) -> int:
    """
    Grant extra credits when student status is verified.
    Called by student.verify_student() after successful verification.

    FUTURE: Called automatically when is_student_verified flips to True.
    """
    student_bonus = DEFAULT_CREDITS["student"] - DEFAULT_CREDITS["free"]
    return add_credits(user_id, student_bonus, reason="student_bonus")
