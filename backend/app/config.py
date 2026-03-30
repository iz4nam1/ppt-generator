"""
config.py
=========
Single source of truth for all configuration.
Add new env vars here — never scattered across files.

FUTURE: When adding plan tiers, add PLAN_CREDITS here.
FUTURE: When adding Razorpay/Stripe, add API keys here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).parent.parent
TEMP_DIR      = BASE_DIR / "temp_files"
TEMPLATES_DIR = BASE_DIR / "saved_templates"
DB_PATH       = BASE_DIR / "deckforge.db"

TEMP_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)

# ── Required env vars ─────────────────────────────────────────────────────────
def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val

GROQ_API_KEY = _require("GROQ_API_KEY")

# ── Optional env vars (with defaults) ─────────────────────────────────────────
ADMIN_KEY       = os.getenv("ADMIN_KEY", "change-me-in-production")
SITE_NAME       = os.getenv("SITE_NAME", "DeckForge")
SITE_URL        = os.getenv("SITE_URL", "https://deckforge.app")
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
ENV             = os.getenv("ENV", "production")
DOCS_ENABLED    = os.getenv("DOCS_ENABLED", "false").lower() == "true"

# ── File limits ───────────────────────────────────────────────────────────────
MAX_CONTEXT_MB      = 10
MAX_CONTEXT_FILES   = 10
MAX_DESCRIPTION_LEN = 3000
MAX_TEMPLATE_MB     = 25
MAX_SAVED_TEMPLATES = 20
CHARS_PER_FILE      = 12_000

# ── Credit system (costs per feature) ────────────────────────────────────────
# FUTURE: Adjust these when real credit system goes live.
# Currently credits are not enforced — just structured for when they are.
CREDIT_COSTS = {
    "ppt_generation":      10,   # costs 10 credits per deck
    "image_generation":    5,    # costs 5 credits per image (placeholder)
    "document_summary":    3,    # costs 3 credits per doc (placeholder)
}

# ── Default credits on signup ─────────────────────────────────────────────────
# FUTURE: Adjust per plan tier
DEFAULT_CREDITS = {
    "free":    50,
    "student": 200,   # students get 4x credits
    "pro":     1000,
}

# ── Daily generation limits per plan ─────────────────────────────────────────
# FUTURE: Enforced in credits.py when payment system is live
DAILY_LIMITS = {
    "free":    5,
    "student": 20,
    "pro":     100,
}

# ── AI models ─────────────────────────────────────────────────────────────────
AI_MODEL_FAST   = "llama-3.1-8b-instant"    # detection, classification
AI_MODEL_MAIN   = "llama-3.3-70b-versatile"  # generation

# ── File type sets ─────────────────────────────────────────────────────────────
TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx", ".html",
    ".css", ".json", ".yaml", ".yml", ".java", ".go", ".rs", ".cpp",
    ".c", ".cs", ".rb", ".sh", ".bash", ".sql", ".xml", ".toml", ".ini",
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

STUDENT_EMAIL_DOMAINS = {
    ".edu", ".ac.in", ".ac.uk", ".ac.nz", ".ac.za", ".ac.jp",
    ".edu.au", ".edu.sg", ".edu.hk", ".edu.in",
}
