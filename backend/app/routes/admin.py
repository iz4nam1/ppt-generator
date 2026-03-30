"""
routes/admin.py
================
Admin-only endpoints. All require ADMIN_KEY query param.

FUTURE:
    - GET  /admin/users/{user_id}      — view single user
    - POST /admin/users/{user_id}/credits — manually grant credits
    - GET  /admin/payments             — payment history
    - POST /admin/verify-student/{uid} — manually verify student
"""

import logging
from fastapi import APIRouter, HTTPException, Request
from app.config import ADMIN_KEY
from app.database import get_db

log    = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(key: str):
    if key != ADMIN_KEY:
        raise HTTPException(403, "Forbidden.")


@router.get("/stats")
async def admin_stats(request: Request, key: str = ""):
    _require_admin(key)
    with get_db() as conn:
        return {
            "total_users":    conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"],
            "students":       conn.execute("SELECT COUNT(*) as c FROM users WHERE is_student=1").fetchone()["c"],
            "verified_students": conn.execute("SELECT COUNT(*) as c FROM users WHERE is_student_verified=1").fetchone()["c"],
            "total_gens":     conn.execute("SELECT COUNT(*) as c FROM generations").fetchone()["c"],
            "by_feature":     [dict(r) for r in conn.execute("SELECT feature, COUNT(*) as c FROM generations GROUP BY feature ORDER BY c DESC").fetchall()],
            "by_type":        [dict(r) for r in conn.execute("SELECT project_type, COUNT(*) as c FROM generations WHERE project_type IS NOT NULL GROUP BY project_type ORDER BY c DESC").fetchall()],
            "by_country":     [dict(r) for r in conn.execute("SELECT country, COUNT(*) as c FROM users GROUP BY country ORDER BY c DESC").fetchall()],
            "top_hackathons": [dict(r) for r in conn.execute("SELECT hackathon, COUNT(*) as c FROM users WHERE hackathon IS NOT NULL GROUP BY hackathon ORDER BY c DESC LIMIT 20").fetchall()],
            "recent_users":   [dict(r) for r in conn.execute("SELECT email, name, hackathon, state, is_student, plan_type, credits, created_at FROM users ORDER BY created_at DESC LIMIT 50").fetchall()],
        }


@router.post("/grant-credits")
async def admin_grant_credits(request: Request, key: str = "",
                               user_id: str = "", amount: int = 0):
    """Manually add credits to a user. FUTURE: Build admin UI around this."""
    _require_admin(key)
    if not user_id or amount <= 0:
        raise HTTPException(400, "user_id and amount required.")
    from app.services.credits import add_credits
    new_balance = add_credits(user_id, amount, reason="admin_grant")
    return {"user_id": user_id, "credits_added": amount, "new_balance": new_balance}
