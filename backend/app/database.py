"""
database.py
===========
Database initialisation and connection management.

FUTURE: Swap sqlite3 for SQLAlchemy + PostgreSQL by replacing
        get_db() with an async SQLAlchemy session — routes stay identical.
FUTURE: Run Alembic migrations instead of CREATE TABLE IF NOT EXISTS.
"""

import logging
import sqlite3
from contextlib import contextmanager
from app.config import DB_PATH

log = logging.getLogger(__name__)


def init_db():
    """
    Create all tables on startup.
    Each table has fields for current AND future features
    so we never need a destructive migration early on.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript("""

        -- ── Users ──────────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS users (
            id                  TEXT PRIMARY KEY,
            email               TEXT UNIQUE NOT NULL,
            name                TEXT,

            -- Credit system (enforced once payment is live)
            credits             INTEGER DEFAULT 50,
            plan_type           TEXT DEFAULT 'free',   -- free | student | pro

            -- Student verification
            is_student          INTEGER DEFAULT 0,
            is_student_verified INTEGER DEFAULT 0,     -- FUTURE: set after ID check
            student_id_document TEXT,                  -- FUTURE: path to uploaded doc

            -- Profile
            university          TEXT,
            state               TEXT,
            country             TEXT DEFAULT 'IN',
            hackathon           TEXT,

            -- Metadata
            created_at          TEXT NOT NULL,
            last_active_at      TEXT,
            gen_count           INTEGER DEFAULT 0
        );

        -- ── Generations ─────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS generations (
            id              TEXT PRIMARY KEY,
            user_id         TEXT,
            feature         TEXT NOT NULL,             -- 'ppt_generation' | future features
            project_type    TEXT,
            slide_count     INTEGER,
            template_name   TEXT,
            gen_id          TEXT,
            credits_used    INTEGER DEFAULT 0,
            created_at      TEXT NOT NULL,
            ip_hash         TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        -- ── Saved templates ──────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS saved_templates (
            id          TEXT PRIMARY KEY,
            user_id     TEXT,
            name        TEXT NOT NULL,
            filename    TEXT NOT NULL,
            slide_count INTEGER,
            is_public   INTEGER DEFAULT 0,
            use_count   INTEGER DEFAULT 0,
            created_at  TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        -- ── Payments ─────────────────────────────────────────────────────────
        -- FUTURE: Populated by payment_service.py when Razorpay/Stripe is wired in
        CREATE TABLE IF NOT EXISTS payments (
            id              TEXT PRIMARY KEY,
            user_id         TEXT NOT NULL,
            amount_inr      REAL,                      -- or amount_usd
            credits_added   INTEGER,
            gateway         TEXT,                      -- 'razorpay' | 'stripe'
            gateway_txn_id  TEXT,
            status          TEXT DEFAULT 'pending',    -- pending | success | failed
            created_at      TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        -- ── Usage log (for rate limiting) ────────────────────────────────────
        -- FUTURE: rate_limit.py reads this table to enforce per-user limits
        CREATE TABLE IF NOT EXISTS usage_log (
            id          TEXT PRIMARY KEY,
            user_id     TEXT,
            feature     TEXT,
            ip_hash     TEXT,
            created_at  TEXT NOT NULL
        );

        """)
    log.info("Database initialised")


@contextmanager
def get_db():
    """
    Yields a sqlite3 connection with Row factory.
    Usage:
        with get_db() as conn:
            conn.execute(...)

    FUTURE: Replace with:
        async with AsyncSession() as session:
            yield session
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
