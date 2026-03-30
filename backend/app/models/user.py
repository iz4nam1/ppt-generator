"""
models/user.py
==============
Pydantic schemas for User — used for request validation and response shaping.

FUTURE: Add UserPro, UserStudent response models with different fields.
FUTURE: Add PaymentHistory model.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserRegisterRequest(BaseModel):
    """What the frontend sends to POST /register"""
    email:      str
    name:       Optional[str] = ""
    hackathon:  Optional[str] = ""
    state:      Optional[str] = ""
    country:    Optional[str] = "IN"
    university: Optional[str] = ""


class UserResponse(BaseModel):
    """What POST /register returns"""
    user_id:    str
    is_student: bool
    plan_type:  str
    credits:    int
    message:    str


class UserProfile(BaseModel):
    """Full user profile — used in /admin/stats and future /me endpoint"""
    id:                  str
    email:               str
    name:                Optional[str]
    credits:             int
    plan_type:           str
    is_student:          bool
    is_student_verified: bool
    university:          Optional[str]
    state:               Optional[str]
    country:             str
    hackathon:           Optional[str]
    gen_count:           int
    created_at:          str
