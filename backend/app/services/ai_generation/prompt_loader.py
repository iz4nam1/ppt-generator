"""
services/ai_generation/prompt_loader.py
=========================================
Loads prompts from the /prompts folder.
Edit prompts/personas.json, archetypes.json, system.txt without touching code.
Prompts are cached in memory — restart server after editing.
"""

import json
import logging
import re
from pathlib import Path
from functools import lru_cache

log = logging.getLogger(__name__)
PROMPTS_DIR = Path(__file__).parent.parent.parent.parent / "prompts"


@lru_cache(maxsize=None)
def load_personas() -> dict:
    path = PROMPTS_DIR / "personas.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Strip metadata keys
    return {k: v for k, v in data.items() if not k.startswith("_")}


@lru_cache(maxsize=None)
def load_archetypes() -> dict:
    path = PROMPTS_DIR / "archetypes.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


@lru_cache(maxsize=None)
def load_system_prompt() -> str:
    path = PROMPTS_DIR / "system.txt"
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def get_persona(project_type: str) -> dict:
    personas = load_personas()
    return personas.get(project_type, personas["technical"])


def get_archetype(slide_title: str) -> dict:
    """Match slide title to archetype by keyword scan."""
    archetypes = load_archetypes()
    title_lower = slide_title.lower()

    for key, arch in archetypes.items():
        if key == "generic":
            continue
        keywords = arch.get("keywords", [])
        if any(kw in title_lower for kw in keywords):
            return arch

    return archetypes["generic"]


def get_slide_tier(slide_title: str) -> int:
    """Return the tier (1/2/3) for a slide based on its archetype."""
    return get_archetype(slide_title).get("tier", 2)


def get_premium_features(slide_title: str) -> list:
    """Return list of premium-locked features for a slide."""
    return get_archetype(slide_title).get("premium_locked", [])


def is_premium_locked(slide_title: str, feature: str, user_plan: str = "free") -> bool:
    """
    Check if a premium feature is locked for this user.
    Currently all premium features are locked for all users (not yet implemented).
    FUTURE: return False for 'pro' and 'student_verified' plans once image gen is live.
    """
    locked_features = get_premium_features(slide_title)
    if feature not in locked_features:
        return False
    # FUTURE: check user_plan here
    # if user_plan in ("pro", "student_verified"):
    #     return False
    return True


def build_slide_prompt(
    slide_title:   str,
    slide_number:  int,
    total_slides:  int,
    brief:         str,
    slide_plan:    dict,
    persona:       dict,
) -> tuple[str, str]:
    """
    Build the (system_prompt, user_prompt) for a single slide.
    Returns a tuple — system goes to system role, user goes to user role.
    """
    system = load_system_prompt()
    archetype = get_archetype(slide_title)

    # Build judge context from persona
    what_impresses = "\n".join(f"  ✓ {w}" for w in persona.get("what_impresses", []))
    what_kills = "\n".join(f"  ✗ {w}" for w in persona.get("what_kills", []))
    forbidden = ", ".join(persona.get("forbidden_words", []))

    # Build slide plan block if available
    plan = slide_plan.get(str(slide_number), {})
    plan_block = ""
    if plan:
        kp = "\n".join(f"    - {p}" for p in plan.get("key_points", []))
        plan_block = f"""
CONTENT PLAN FOR THIS SLIDE (from the planning phase):
  Angle to take: {plan.get('angle', 'direct answer to slide title')}
  Lead with: {plan.get('opening', 'most important fact first')}
  Key facts to use:
{kp}
  Do NOT cover (belongs on other slides): {plan.get('avoid', 'nothing specific')}
"""

    # Build structure guidance
    structure = "\n".join(
        f"  {i+1}. {s}" for i, s in enumerate(archetype.get("structure", []))
    )

    system_with_persona = f"""{system}

═══════════════════════════════════════════
PROJECT TYPE: {persona['label']}
JUDGE PROFILE: {persona['judge_profile']}
WRITE IN THIS VOICE: {persona['voice']}

WHAT IMPRESSES THIS JUDGE:
{what_impresses}

WHAT KILLS YOUR SUBMISSION WITH THIS JUDGE:
{what_kills}

ADDITIONAL FORBIDDEN WORDS FOR THIS TYPE: {forbidden}

BAD EXAMPLE (never write like this):
{persona['example_bad']}

GOOD EXAMPLE (aim for this level of specificity):
{persona['example_good']}
═══════════════════════════════════════════"""

    user_prompt = f"""PROJECT BRIEF (all verified facts — do not invent beyond this):
{brief}

SLIDE {slide_number} of {total_slides}: "{slide_title}"

WHAT JUDGES EXPECT FROM THIS SLIDE TYPE:
{archetype['judge_expectation']}

HOW TO STRUCTURE THIS SLIDE:
{structure}

QUALITY TEST (ask yourself before finishing):
{archetype['depth_test']}

LINE FORMAT GUIDE:
{archetype.get('line_format', 'Direct, specific, evidence-backed sentences.')}
{plan_block}
Write 4-6 content lines for this slide.
Do not repeat the slide title. No preamble. No bullets. No headers.
Pull specific names, numbers, and decisions from the brief above.
If the brief does not contain a needed fact, write around it — do not invent."""

    return system_with_persona, user_prompt
