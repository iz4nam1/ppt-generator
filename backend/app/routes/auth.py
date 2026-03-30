"""
routes/auth.py
==============
User registration and auth endpoints.

FUTURE:
    - POST /auth/login    (email + OTP or password)
    - POST /auth/logout
    - GET  /me            (current user profile + credits)
    - GET  /me/usage      (usage stats)
    - POST /verify/student-id  (upload student ID for verification)
"""

import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, Form, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.services.student import detect_student_status
from app.utils.security import sanitize_text, validate_email
from app.config import DEFAULT_CREDITS

log     = logging.getLogger(__name__)
router  = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/register")
@limiter.limit("20/minute")
async def register(
    request:    Request,
    email:      str  = Form(...),
    name:       str  = Form(default=""),
    hackathon:  str  = Form(default=""),
    state:      str  = Form(default=""),
    country:    str  = Form(default="IN"),
    university: str  = Form(default=""),
):
    """
    Register or update a user.
    Returns user_id which the frontend stores in localStorage.

    Ideas and project content are NEVER stored here.
    Only: email, name, hackathon, state, country, university.
    """
    email = sanitize_text(email, 254).lower()
    if not validate_email(email):
        raise HTTPException(400, "Please enter a valid email address.")

    name       = sanitize_text(name, 100)
    hackathon  = sanitize_text(hackathon, 200)
    state      = sanitize_text(state, 100)
    country    = sanitize_text(country, 50)
    university = sanitize_text(university, 200)
    is_student = detect_student_status(email, university)
    plan_type  = "student" if is_student else "free"
    credits    = DEFAULT_CREDITS[plan_type]

    try:
        with get_db() as conn:
            existing = conn.execute(
                "SELECT id, credits, plan_type FROM users WHERE email=?", (email,)
            ).fetchone()

            if existing:
                user_id   = existing["id"]
                credits   = existing["credits"]
                plan_type = existing["plan_type"]
                if hackathon:
                    conn.execute(
                        "UPDATE users SET hackathon=?, state=?, name=?, last_active_at=? WHERE id=?",
                        (hackathon, state, name or None, datetime.utcnow().isoformat(), user_id)
                    )
            else:
                user_id = uuid.uuid4().hex
                conn.execute(
                    """INSERT INTO users
                       (id, email, name, credits, plan_type, is_student,
                        university, state, country, hackathon, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (user_id, email, name or None, credits, plan_type,
                     int(is_student), university or None, state or None,
                     country, hackathon or None, datetime.utcnow().isoformat())
                )

        log.info(f"User registered: ***@{email.split('@')[-1]} | student={is_student}")

        return {
            "user_id":    user_id,
            "is_student": is_student,
            "plan_type":  plan_type,
            "credits":    credits,
            "message":    "Welcome! Your ideas and project content will never be stored.",
        }

    except Exception as e:
        log.error(f"Register error: {e}")
        raise HTTPException(500, "Registration failed. Please try again.")
