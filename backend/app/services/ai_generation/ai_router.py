"""
services/ai_generation/ai_router.py
=====================================
Multi-provider AI router.

PROVIDERS:
  Gemini Flash  → primary, 1500 req/day, best quality, 1M context
  Groq 70b      → secondary, 500 req/day, fast, great structured output
  Cerebras      → tertiary, unlimited*, insane speed (2000 tok/s)
  Groq 8b       → classification only, 14400 req/day

ROUTING BY SLIDE TIER:
  Tier 1 (critical slides)  → Gemini + Groq race in parallel, pick best
  Tier 2 (important slides) → Groq 70b with Gemini fallback
  Tier 3 (supporting)       → Cerebras with Groq fallback

ROUTING BY TASK:
  Project detection    → Groq 8b  (tiny task, 20K TPM)
  Context compression  → Cerebras (fast, unlimited, just extraction)
  Slide planning       → Gemini   (needs full context, big picture)
  Slide generation     → tier-based above
"""

import asyncio
import logging
import os
import re
import time

log = logging.getLogger(__name__)

# ── Provider availability flags ───────────────────────────────────────────────
HAS_GEMINI   = False
HAS_CEREBRAS = False
HAS_GROQ     = False

groq_client     = None
gemini_client   = None
cerebras_client = None


def _init_providers():
    global HAS_GEMINI, HAS_CEREBRAS, HAS_GROQ
    global groq_client, gemini_client, cerebras_client

    # ── Groq ──────────────────────────────────────────────────────────────────
    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key:
        try:
            from groq import Groq
            groq_client = Groq(api_key=groq_key)
            HAS_GROQ = True
            log.info("✓ Groq loaded")
        except ImportError:
            log.warning("groq not installed — pip install groq")
        except Exception as e:
            log.warning(f"Groq init failed: {e}")

    # ── Gemini (new google-genai package) ─────────────────────────────────────
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if gemini_key:
        try:
            from google import genai
            gemini_client = genai.Client(api_key=gemini_key)
            HAS_GEMINI = True
            log.info("✓ Gemini 2.0 Flash loaded")
        except ImportError:
            log.warning("google-genai not installed — pip install google-genai")
        except Exception as e:
            log.warning(f"Gemini init failed: {e}")

    # ── Cerebras ──────────────────────────────────────────────────────────────
    cerebras_key = os.getenv("CEREBRAS_API_KEY", "")
    if cerebras_key:
        try:
            from cerebras.cloud.sdk import Cerebras
            cerebras_client = Cerebras(api_key=cerebras_key)
            HAS_CEREBRAS = True
            log.info("✓ Cerebras loaded")
        except ImportError:
            log.warning("cerebras-cloud-sdk not installed — pip install cerebras-cloud-sdk")
        except Exception as e:
            log.warning(f"Cerebras init failed: {e}")

    available = [p for p, v in [
        ("Groq", HAS_GROQ),
        ("Gemini", HAS_GEMINI),
        ("Cerebras", HAS_CEREBRAS)
    ] if v]

    log.info(f"AI providers available: {available}")

    if not available:
        raise RuntimeError("No AI providers available. Check GROQ_API_KEY in .env")


_init_providers()


# ═══════════════════════════════════════════════════════════════════════════════
#  INDIVIDUAL PROVIDER CALLERS
# ═══════════════════════════════════════════════════════════════════════════════

def _groq_call(
    prompt:     str,
    system:     str  = "",
    model:      str  = "llama-3.3-70b-versatile",
    max_tokens: int  = 1000,
    json_mode:  bool = False,
    label:      str  = "",
) -> str:
    if not HAS_GROQ or not groq_client:
        return ""

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    kwargs = dict(
        model       = model,
        messages    = messages,
        max_tokens  = max_tokens,
        temperature = 0.35,
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    for attempt in range(3):
        try:
            r = groq_client.chat.completions.create(**kwargs)
            return r.choices[0].message.content.strip()
        except Exception as e:
            err = str(e)
            if "429" in err and attempt < 2:
                wait = 10 * (attempt + 1)
                log.warning(f"Groq 429 on {label}, waiting {wait}s")
                time.sleep(wait)
            else:
                log.warning(f"Groq failed on {label}: {type(e).__name__}")
                return ""
    return ""


def _gemini_call(
    prompt:    str,
    system:    str  = "",
    json_mode: bool = False,
    label:     str  = "",
) -> str:
    if not HAS_GEMINI or not gemini_client:
        return ""
    try:
        from google.genai import types

        full = f"{system}\n\n{prompt}" if system else prompt
        if json_mode:
            full += "\n\nReturn ONLY valid JSON. No markdown fences. No text outside the JSON."

        response = gemini_client.models.generate_content(
            model    = "gemini-2.0-flash",
            contents = full,
            config   = types.GenerateContentConfig(
                temperature      = 0.35,
                max_output_tokens = 1000,
            ),
        )
        return response.text.strip()
    except Exception as e:
        err = str(e)
        if "429" in err or "quota" in err.lower():
            log.warning(f"Gemini quota hit on {label}")
        else:
            log.warning(f"Gemini failed on {label}: {type(e).__name__}")
        return ""


def _cerebras_call(
    prompt:     str,
    system:     str = "",
    max_tokens: int = 1000,
    label:      str = "",
) -> str:
    if not HAS_CEREBRAS or not cerebras_client:
        return ""
    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        r = cerebras_client.chat.completions.create(
            model      = "llama-3.3-70b",   # correct Cerebras model name
            messages   = messages,
            max_tokens = max_tokens,
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        log.warning(f"Cerebras failed on {label}: {type(e).__name__}")
        return ""


# ═══════════════════════════════════════════════════════════════════════════════
#  QUALITY SCORER — picks the better of two parallel responses
# ═══════════════════════════════════════════════════════════════════════════════

def _score_response(text: str) -> float:
    """Score a response for quality. Higher = better."""
    if not text or len(text) < 50:
        return 0.0

    score = 0.0
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # Good: 4-6 lines
    if 4 <= len(lines) <= 6:
        score += 2.0
    elif len(lines) < 3:
        score -= 2.0

    for line in lines:
        if re.search(r'\d+', line):      score += 0.3  # has numbers
        if len(line.split()) >= 8:       score += 0.2  # not too short
        if len(line.split()) <= 20:      score += 0.1  # not too long

    # Penalise hallucination signals
    bad_phrases = [
        "cutting-edge", "innovative", "robust", "seamless",
        "our solution", "we believe", "this feature",
        "significantly better", "state-of-the-art",
    ]
    for phrase in bad_phrases:
        if phrase.lower() in text.lower():
            score -= 0.5

    if len(text) < 200:
        score -= 1.0

    return score


# ═══════════════════════════════════════════════════════════════════════════════
#  ROUTING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

async def call_tier1(prompt: str, system: str = "", label: str = "") -> str:
    """
    Tier 1 — Critical slides: Problem, Solution, Architecture, Impact.
    Fires Gemini + Groq in PARALLEL. Returns the better response.
    Zero extra time — both run simultaneously.
    """
    loop = asyncio.get_event_loop()

    gemini_future = loop.run_in_executor(
        None, _gemini_call, prompt, system, False, f"{label}-gem"
    )
    groq_future = loop.run_in_executor(
        None, _groq_call, prompt, system,
        "llama-3.3-70b-versatile", 1000, False, f"{label}-groq"
    )

    results = await asyncio.gather(gemini_future, groq_future, return_exceptions=True)

    gemini_result = results[0] if not isinstance(results[0], Exception) else ""
    groq_result   = results[1] if not isinstance(results[1], Exception) else ""

    gem_score  = _score_response(gemini_result)
    groq_score = _score_response(groq_result)

    log.info(f"[{label}] Tier1 race — Gemini: {gem_score:.1f}, Groq: {groq_score:.1f}")

    if gem_score >= groq_score and gemini_result:
        return gemini_result
    if groq_result:
        return groq_result
    if gemini_result:
        return gemini_result
    return ""


async def call_tier2(prompt: str, system: str = "", label: str = "") -> str:
    """
    Tier 2 — Important slides: Features, Tech, Process, Performance.
    Groq 70b primary → Gemini fallback.
    """
    loop   = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, _groq_call, prompt, system,
        "llama-3.3-70b-versatile", 1000, False, label
    )
    if result:
        return result

    log.info(f"[{label}] Tier2 Groq failed — trying Gemini")
    return await loop.run_in_executor(
        None, _gemini_call, prompt, system, False, f"{label}-fallback"
    )


async def call_tier3(prompt: str, system: str = "", label: str = "") -> str:
    """
    Tier 3 — Supporting slides: Team, Cost, Roadmap, Assets, Wireframes.
    Cerebras primary (unlimited) → Groq fallback.
    """
    loop   = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, _cerebras_call, prompt, system, 1000, label
    )
    if result:
        return result

    log.info(f"[{label}] Tier3 Cerebras failed — trying Groq")
    return await loop.run_in_executor(
        None, _groq_call, prompt, system,
        "llama-3.3-70b-versatile", 1000, False, f"{label}-fallback"
    )


async def call_by_tier(tier: int, prompt: str, system: str = "", label: str = "") -> str:
    """Route to the correct tier function."""
    if tier == 1:
        return await call_tier1(prompt, system, label)
    elif tier == 2:
        return await call_tier2(prompt, system, label)
    else:
        return await call_tier3(prompt, system, label)


async def call_for_planning(prompt: str, label: str = "plan") -> str:
    """
    Slide planning — needs big picture thinking across all slides.
    Gemini (1M context) first → Groq fallback. JSON output.
    """
    loop   = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, _gemini_call, prompt, "", True, label
    )
    if result:
        return result

    return await loop.run_in_executor(
        None, _groq_call, prompt, "",
        "llama-3.3-70b-versatile", 2000, True, f"{label}-fallback"
    )


async def call_for_compression(prompt: str, label: str = "compress") -> str:
    """
    Context compression — pure extraction, no creativity needed.
    Cerebras (fast, unlimited) first → Groq fallback.
    """
    loop   = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, _cerebras_call, prompt, "", 1400, label
    )
    if result:
        return result

    return await loop.run_in_executor(
        None, _groq_call, prompt, "",
        "llama-3.3-70b-versatile", 1400, False, f"{label}-fallback"
    )


def call_for_detection(description: str, context_sample: str) -> str:
    """
    Project type classification — tiny task, called once per generation.
    Groq 8b (20K TPM, fastest) → Gemini fallback.
    Synchronous.
    """
    prompt = (
        f"Classify into exactly ONE category: "
        f"technical, social_impact, business, research, design, policy\n\n"
        f"Project: {description}\n"
        f"Context: {context_sample[:1000]}\n\n"
        f"Reply with ONLY the category word, nothing else."
    )

    result = _groq_call(
        prompt, model="llama-3.1-8b-instant", max_tokens=5, label="detect"
    )
    if result:
        return result

    result = _gemini_call(prompt, label="detect-fallback")
    return result.lower().strip() if result else "technical"
