"""
routes/templates.py
====================
Saved template management endpoints.
"""

import io
import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pptx import Presentation
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import MAX_TEMPLATE_MB, MAX_SAVED_TEMPLATES, TEMPLATES_DIR
from app.database import get_db
from app.utils.security import sanitize_filename, sanitize_text, validate_magic

log     = logging.getLogger(__name__)
router  = APIRouter(prefix="/templates", tags=["templates"])
limiter = Limiter(key_func=get_remote_address)


@router.get("")
@limiter.limit("30/minute")
async def list_templates(request: Request, user_id: str):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, name, slide_count, is_public, use_count, created_at
               FROM saved_templates
               WHERE user_id=? OR is_public=1
               ORDER BY use_count DESC, created_at DESC""",
            (user_id,)
        ).fetchall()
    return {"templates": [dict(r) for r in rows]}


@router.post("/save")
@limiter.limit("10/minute")
async def save_template(
    request:   Request,
    template:  UploadFile = File(...),
    name:      str        = Form(...),
    user_id:   str        = Form(...),
    is_public: bool       = Form(default=False),
):
    if not user_id or len(user_id) < 10:
        raise HTTPException(400, "Valid user_id required.")
    safe_name = sanitize_text(name, 100)
    if not safe_name:
        raise HTTPException(400, "Template name required.")

    with get_db() as conn:
        if not conn.execute("SELECT id FROM users WHERE id=?", (user_id,)).fetchone():
            raise HTTPException(403, "Unknown user.")
        count = conn.execute(
            "SELECT COUNT(*) as c FROM saved_templates WHERE user_id=?", (user_id,)
        ).fetchone()["c"]
        if count >= MAX_SAVED_TEMPLATES:
            raise HTTPException(400, f"Maximum {MAX_SAVED_TEMPLATES} templates reached.")

    data = await template.read()
    if len(data) > MAX_TEMPLATE_MB * 1024 * 1024:
        raise HTTPException(400, f"Template exceeds {MAX_TEMPLATE_MB}MB.")
    sf = sanitize_filename(template.filename or "template.pptx")
    if not sf.lower().endswith(".pptx"): raise HTTPException(400, "Only .pptx allowed.")
    if not validate_magic(data, sf):     raise HTTPException(400, "Invalid .pptx.")

    try:
        slide_count = len(Presentation(io.BytesIO(data)).slides)
    except Exception:
        slide_count = 0

    tpl_id   = uuid.uuid4().hex
    tpl_path = TEMPLATES_DIR / f"{tpl_id}_{sf}"
    tpl_path.write_bytes(data)

    with get_db() as conn:
        conn.execute(
            """INSERT INTO saved_templates
               (id, user_id, name, filename, slide_count, is_public, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (tpl_id, user_id, safe_name, str(tpl_path),
             slide_count, int(is_public), datetime.utcnow().isoformat())
        )
    return {"template_id": tpl_id, "name": safe_name, "slide_count": slide_count}


@router.delete("/{template_id}")
@limiter.limit("10/minute")
async def delete_template(request: Request, template_id: str, user_id: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT filename, user_id FROM saved_templates WHERE id=?", (template_id,)
        ).fetchone()
        if not row:            raise HTTPException(404, "Not found.")
        if row["user_id"] != user_id: raise HTTPException(403, "Not your template.")
        try: Path(row["filename"]).unlink(missing_ok=True)
        except: pass
        conn.execute("DELETE FROM saved_templates WHERE id=?", (template_id,))
    return {"deleted": True}
