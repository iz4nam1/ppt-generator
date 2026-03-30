"""
models/generation.py
====================
Pydantic schemas for AI generation jobs and templates.
"""

from pydantic import BaseModel
from typing import Optional, List


class GenerationStartResponse(BaseModel):
    """Returned immediately by POST /generate/start"""
    job_id: str


class SavedTemplate(BaseModel):
    id:         str
    name:       str
    slide_count: Optional[int]
    is_public:  bool
    use_count:  int
    created_at: str


class TemplateListResponse(BaseModel):
    templates: List[SavedTemplate]


class SaveTemplateResponse(BaseModel):
    template_id: str
    name:        str
    slide_count: int
