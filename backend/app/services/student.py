"""
services/student.py
===================
Student verification service.

CURRENT STATE:
  - Auto-detects student by email domain
  - is_student_verified stays False (not confirmed)

HOW TO ACTIVATE FULL VERIFICATION:
  Step 1: Email-based — already done (domain check)
  Step 2: Upload ID  — add endpoint POST /verify/student-id
          Store document path in users.student_id_document
          Set is_student_verified=True after manual/automated review
  Step 3: Credits bonus automatically applied via grant_student_bonus()

FUTURE integrations:
  - SheerID API (automated .edu verification)
  - Manual admin review dashboard
  - University email OTP verification
"""

import logging
import re
from app.database import get_db
from app.config import STUDENT_EMAIL_DOMAINS

log = logging.getLogger(__name__)


def is_student_email(email: str) -> bool:
    """
    Check if email domain matches known student domains.
    This is the first (weakest) form of verification.
    """
    domain = email.lower().split("@")[-1] if "@" in email else ""
    return any(domain.endswith(sd) for sd in STUDENT_EMAIL_DOMAINS)


def detect_student_status(email: str, university: str = "") -> bool:
    """
    Auto-detect student status on registration.
    Sets is_student=True but NOT is_student_verified=True.

    Verified status requires additional steps (see verify_student below).
    """
    return is_student_email(email) or bool(university)


def verify_student(user_id: str, method: str = "email") -> dict:
    """
    Verify a user's student status and grant benefits.

    CURRENT:  Placeholder — logs intent, does not verify
    FUTURE:   Implement based on `method`:
              - 'email'    : confirm .edu email via OTP
              - 'id_upload': review uploaded student ID document
              - 'sheerid'  : call SheerID API for automated check

    Args:
        user_id: User to verify
        method:  Verification method to use

    Returns:
        dict with status and message

    WIRING:
        When this returns success=True, call:
            credits.grant_student_bonus(user_id)
            # and update plan_type to 'student'
    """
    log.info(f"[PLACEHOLDER] verify_student called for {user_id} via {method}")

    # TODO: Implement real verification
    # Example for 'email' method:
    #   1. Send OTP to student email
    #   2. User confirms OTP via POST /verify/student-otp
    #   3. On success: set is_student_verified=True, plan_type='student'
    #   4. Call credits.grant_student_bonus(user_id)

    return {
        "success":  False,
        "verified": False,
        "message":  "Student verification not yet implemented. Coming soon.",
        "method":   method,
    }


def upload_student_document(user_id: str, document_path: str) -> dict:
    """
    Store path to uploaded student ID document for review.

    CURRENT:  Placeholder
    FUTURE:   
        1. Store document_path in users.student_id_document
        2. Notify admin for manual review
        3. OR call OCR/AI service to auto-verify
        4. On approval: call verify_student(user_id, method='id_upload')
    """
    log.info(f"[PLACEHOLDER] Student document upload for {user_id}: {document_path}")

    # TODO: Store in DB and trigger review workflow
    return {
        "success": False,
        "message": "Document upload verification coming soon.",
    }


def get_student_benefits(plan_type: str) -> dict:
    """
    Returns what benefits a student gets.
    Used to show users what they unlock by verifying.
    """
    return {
        "extra_credits":    150,   # 200 vs 50 default
        "daily_limit":      20,    # vs 5 for free
        "priority_queue":   False, # FUTURE: faster generation
        "exclusive_themes": False, # FUTURE: premium templates
    }
