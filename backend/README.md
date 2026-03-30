# DeckForge Backend v2.0

AI-powered PPT generator for hackathons. Clean, modular, built to scale.

## Folder Structure

```
app/
├── main.py                          # FastAPI app — wires everything together
├── config.py                        # All env vars and constants
├── database.py                      # SQLite setup + get_db() context manager
│
├── routes/                          # HTTP layer — thin, no business logic
│   ├── auth.py                      # POST /auth/register
│   ├── generate.py                  # POST /generate/start, GET /generate/stream/{id}
│   ├── templates.py                 # GET/POST/DELETE /templates
│   ├── payments.py                  # POST /payments/create-order, /verify, /webhook
│   └── admin.py                     # GET /admin/stats (requires ADMIN_KEY)
│
├── services/
│   ├── credits.py                   # check/deduct/add credits (flip CREDITS_ENFORCED=True)
│   ├── student.py                   # student detection + verification (placeholder)
│   ├── rate_limit.py                # per-user rate limiting (daily limits active now)
│   └── ai_generation/
│       ├── base.py                  # AIFeature base class — all features inherit this
│       ├── __init__.py              # FEATURE_REGISTRY — register new features here
│       ├── ppt_service.py           # ✅ LIVE — full 3-phase PPT generation pipeline
│       ├── image_service.py         # 🔜 Placeholder — implement with Replicate/Stability
│       └── document_service.py      # 🔜 Placeholder — implement with Groq
│
├── payments/
│   └── payment_service.py           # 🔜 Placeholder — implement Razorpay or Stripe
│
├── models/
│   ├── user.py                      # Pydantic schemas for User
│   └── generation.py                # Pydantic schemas for Generation
│
├── middleware/
│   └── usage_logger.py              # Request logging middleware
│
└── utils/
    └── security.py                  # sanitize, validate, hash helpers
```

## Quickstart

```bash
# Install
pip install -r requirements.txt

# Set up env
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# Run
uvicorn app.main:app --reload --port 8001
```

## How to Add a New AI Feature

1. Create `app/services/ai_generation/your_feature.py`
2. Class inherits `AIFeature`, sets `FEATURE_KEY`, implements `run()`
3. Add credit cost to `config.CREDIT_COSTS`
4. Register in `app/services/ai_generation/__init__.py`
5. Add a route in `app/routes/generate.py` if needed

Credits, rate-limiting, usage logging all work automatically.

## How to Activate Credits

1. Set up payment gateway (see `payments/payment_service.py`)
2. Flip `CREDITS_ENFORCED = True` in `services/credits.py`
3. Done — no route changes needed

## Deployment (Render)

| Field | Value |
|---|---|
| Root Directory | `.` (repo root) |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

Add all env vars from `.env.example` in Render's Environment tab.
