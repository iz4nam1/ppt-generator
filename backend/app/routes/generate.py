"""
routes/generate.py
==================
AI generation endpoints.

CURRENT:  PPT generation only.
FUTURE:   Add routes for image_generation, document_summary, etc.
          Each new feature follows the same pattern:
            1. POST /generate/{feature}/start  → returns job_id
            2. GET  /generate/stream/{job_id}  → SSE progress
            3. GET  /generate/download/{job_id}→ file download
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import (
    MAX_CONTEXT_FILES, MAX_CONTEXT_MB, MAX_TEMPLATE_MB, TEMP_DIR
)
from app.database import get_db
from app.services.ai_generation import get_feature_service
from app.services.ai_generation.ppt_service import process_context_file
from app.services.credits import InsufficientCreditsError
from app.services.rate_limit import RateLimitExceededError
from app.utils.security import sanitize_description, sanitize_filename, validate_magic, hash_ip

log     = logging.getLogger(__name__)
router  = APIRouter(prefix="/generate", tags=["generate"])
limiter = Limiter(key_func=get_remote_address)

# In-memory job store: job_id → {"status", "output_path", "queue"}
# FUTURE: Replace with Redis for multi-worker deployments
JOBS: dict = {}


def _get_user_plan(user_id: str) -> str:
    """Get user's plan type from DB. Returns 'free' if not found."""
    if not user_id:
        return "free"
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT plan_type FROM users WHERE id=?", (user_id,)
            ).fetchone()
        return row["plan_type"] if row else "free"
    except Exception:
        return "free"


async def _run_generation_job(job_id: str, job_data: dict):
    """
    Background task that runs the full generation pipeline.
    Pushes SSE events to the job's queue as progress happens.
    """

    def push(event_type: str, message: str, extra: dict = None):
        payload = {"type": event_type, "message": message}
        if extra:
            payload.update(extra)
        JOBS[job_id]["queue"].put_nowait(json.dumps(payload))

    try:
        service = get_feature_service(
            feature_key = job_data["feature"],
            user_id     = job_data.get("user_id", ""),
            plan_type   = job_data.get("plan_type", "free"),
            ip_hash     = job_data.get("ip_hash", ""),
        )

        # PPT generation — pass all required args
        output_path = await service.execute(
            template_path  = job_data["template_path"],
            description    = job_data["description"],
            chunks         = job_data["chunks"],
            generation_id  = job_data["generation_id"],
            push           = push,
        )

        if not output_path:
            return  # error already pushed inside service

        JOBS[job_id]["output_path"] = output_path
        JOBS[job_id]["status"]      = "done"

        # Log to DB
        try:
            with get_db() as conn:
                conn.execute(
                    """INSERT INTO generations
                       (id, user_id, feature, project_type, slide_count,
                        template_name, gen_id, credits_used, created_at, ip_hash)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (uuid.uuid4().hex, job_data.get("user_id") or None,
                     job_data["feature"], None, None,
                     job_data.get("template_name", ""), job_data["generation_id"],
                     0, datetime.utcnow().isoformat(), job_data.get("ip_hash",""))
                )
                if job_data.get("user_id"):
                    conn.execute(
                        "UPDATE users SET gen_count=gen_count+1, last_active_at=? WHERE id=?",
                        (datetime.utcnow().isoformat(), job_data["user_id"])
                    )
        except Exception as e:
            log.warning(f"DB log failed (non-fatal): {e}")

        push("done", "Your presentation is ready!", {"job_id": job_id})

    except (InsufficientCreditsError, RateLimitExceededError) as e:
        push("error", str(e))
    except Exception as e:
        log.error(f"Job {job_id} failed: {e}", exc_info=True)
        push("error", "Something went wrong. Please try again.")
    finally:
        try:
            Path(job_data.get("template_path","")).unlink(missing_ok=True)
        except Exception:
            pass


@router.post("/start")
@limiter.limit("5/minute")
async def generation_start(
    request:       Request,
    template:      UploadFile       = File(...),
    description:   str              = Form(...),
    user_id:       str              = Form(default=""),
    context_files: list[UploadFile] = File(default=[]),
    feature:       str              = Form(default="ppt_generation"),
):
    """
    Start an AI generation job.
    Returns job_id immediately — client connects to /stream/{job_id} for progress.
    """
    if not template.filename:
        raise HTTPException(400, "No template file provided.")
    safe_name = sanitize_filename(template.filename)
    if not safe_name.lower().endswith(".pptx"):
        raise HTTPException(400, "Template must be a .pptx file.")

    description = sanitize_description(description)
    if not description:
        raise HTTPException(400, "Project description cannot be empty.")
    if len(context_files) > MAX_CONTEXT_FILES:
        raise HTTPException(400, f"Maximum {MAX_CONTEXT_FILES} context files allowed.")

    # Validate template
    template_data = await template.read()
    if len(template_data) > MAX_TEMPLATE_MB * 1024 * 1024:
        raise HTTPException(400, f"Template exceeds {MAX_TEMPLATE_MB}MB.")
    if not validate_magic(template_data, safe_name):
        raise HTTPException(400, "Invalid .pptx file.")

    # Process context files
    chunks = []
    for upload in context_files:
        if not upload.filename: continue
        uname = sanitize_filename(upload.filename)
        data  = await upload.read()
        if len(data) > MAX_CONTEXT_MB * 1024 * 1024:
            raise HTTPException(400, f"'{uname}' exceeds {MAX_CONTEXT_MB}MB.")
        if not validate_magic(data, uname):
            continue
        chunks.append(process_context_file(uname, data))

    # Save template to disk for background task
    job_id        = uuid.uuid4().hex
    gen_id        = uuid.uuid4().hex
    template_path = TEMP_DIR / f"{job_id}_template.pptx"
    template_path.write_bytes(template_data)

    plan_type = _get_user_plan(user_id)

    JOBS[job_id] = {"status": "running", "output_path": None, "queue": asyncio.Queue()}

    asyncio.create_task(_run_generation_job(job_id, {
        "feature":       feature,
        "description":   description,
        "template_path": str(template_path),
        "template_name": safe_name,
        "chunks":        chunks,
        "user_id":       user_id,
        "plan_type":     plan_type,
        "generation_id": gen_id,
        "ip_hash":       hash_ip(get_remote_address(request)),
    }))

    return {"job_id": job_id}


@router.get("/stream/{job_id}")
async def generation_stream(job_id: str):
    """SSE endpoint — streams live progress events to the frontend."""
    if job_id not in JOBS:
        raise HTTPException(404, "Job not found.")

    async def event_generator():
        queue = JOBS[job_id]["queue"]
        yield f"data: {json.dumps({'type':'connected','message':'Connected — starting generation...'})}\n\n"
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=15.0)
                yield f"data: {msg}\n\n"
                if json.loads(msg)["type"] in ("done", "error"):
                    break
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'type':'heartbeat','message':'Still working...'})}\n\n"
        await asyncio.sleep(120)
        JOBS.pop(job_id, None)

    return StreamingResponse(
        event_generator(),
        media_type = "text/event-stream",
        headers    = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/download/{job_id}")
async def generation_download(job_id: str):
    """Download the finished file. Only works after SSE sends 'done'."""
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found or expired.")
    if job["status"] != "done":
        raise HTTPException(400, "Presentation not ready yet.")
    output_path = Path(job["output_path"])
    if not output_path.exists():
        raise HTTPException(404, "File not found — may have expired.")

    async def cleanup():
        await asyncio.sleep(30)
        try: output_path.unlink(missing_ok=True)
        except: pass
        JOBS.pop(job_id, None)

    asyncio.create_task(cleanup())
    return FileResponse(
        str(output_path),
        media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename   = "generated_presentation.pptx",
    )
