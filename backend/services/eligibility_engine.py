"""
Eligibility engine — two backends, one interface.

Ollama path:
  1. Pre-compute the key eligibility facts for each program (income vs FPL limits,
     demographic checks, state-specific rules).
  2. Send Gemma a *simplified* prompt where the comparisons are already done —
     it only needs to confirm eligibility and write a plain-language reason.
     This avoids triggering Gemma4's thinking mode, which consumes all num_predict
     tokens before producing any visible output on complex analytical prompts.
  3. If a Gemma batch fails, fall back to the rule-based engine for those programs.

Gemini API path:
  Full Gemma batch reasoning runs in parallel — used for the Kaggle demo.
"""

import asyncio
import json
import logging
import os
from typing import List, Optional

from models.schemas import UserProfile, EligibilityResult, EligibilityResponse
from services.gemma import generate
from utils.fpl import get_fpl, get_fpl_percentage
from utils.formatting import safe_parse_json

logger = logging.getLogger(__name__)

BENEFITS_DIR = os.path.join(os.path.dirname(__file__), "../data/benefits")
FEDERAL_BENEFITS_PATH = os.path.join(BENEFITS_DIR, "federal_programs.json")
STATE_PROGRAMS_DIR = os.path.join(BENEFITS_DIR, "state_programs")
STATE_METADATA_PATH = os.path.join(BENEFITS_DIR, "state_metadata.json")

_state_metadata_cache: dict | None = None

# 3 programs per batch: proven safe for gemma4:e4b on Ollama.
BATCH_SIZE = 3

# Static next-steps per program type — avoids asking Gemma to generate them
# (lengthens output and increases chance of thinking-token overflow on Ollama).
_NEXT_STEPS: dict[str, list[str]] = {
    "snap": [
        "Apply online at your state SNAP office or at benefits.gov",
        "Gather pay stubs (last 30 days), photo ID, and proof of address",
        "Ask about expedited benefits — if monthly income is under $150 you may receive food within 7 days",
    ],
    "medicaid": [
        "Apply at healthcare.gov or your state Medicaid office",
        "Gather proof of income, photo ID, and Social Security numbers for all applicants",
        "Coverage can be retroactive up to 3 months before the application date",
    ],
    "chip": [
        "Apply at insurekidsnow.gov or your state CHIP office",
        "Gather the child's birth certificate and proof of household income",
        "Coverage typically starts quickly after approval",
    ],
    "liheap": [
        "Find your local Community Action Agency at liheapch.acf.hhs.gov",
        "Apply early in the season (October–November for heating) — funds run out quickly",
        "Bring your most recent utility bill, photo ID, and proof of income",
    ],
    "wic": [
        "Find your nearest WIC office at wic.fns.usda.gov/local-agencies",
        "Eligibility is usually confirmed the same day as your appointment",
        "Bring proof of pregnancy or birth certificate, income proof, and photo ID",
    ],
    "ssi": [
        "Apply online at ssa.gov or call 1-800-772-1213",
        "Gather birth certificate, photo ID, medical records if disability applies",
        "Processing takes 3–6 months — apply as soon as possible",
    ],
    "tanf": [
        "Apply at your state welfare or human services office",
        "Bring birth certificates for all children, proof of income, and photo ID",
        "Be aware of the 60-month federal lifetime limit on TANF benefits",
    ],
    "aca_subsidies": [
        "Visit healthcare.gov during open enrollment (November 1 – January 15)",
        "Use the marketplace plan finder to compare subsidized plans",
        "Life events (job loss, birth, move) open a Special Enrollment Period",
    ],
    "lifeline": [
        "Apply at lifelinesupport.org or through your current phone/internet provider",
        "Proof of income or program participation (SNAP, Medicaid) required",
        "Only one Lifeline benefit per household",
    ],
    "housing_choice_voucher": [
        "Apply to every open waiting list at your local Public Housing Authority (PHA)",
        "Find open waiting lists at hud.gov",
        "Ask about emergency preferences for families with children while you wait",
    ],
    "eitc": [
        "File a federal tax return — even at very low income — to claim the EITC",
        "Use IRS Free File (free for incomes under $79,000) at irs.gov/freefile",
        "EITC is paid as a lump-sum tax refund, not monthly — plan accordingly",
    ],
    "child_tax_credit": [
        "File a federal tax return to claim the credit",
        "Use IRS Free File or a free VITA site for tax preparation",
        "The refundable Additional CTC (up to $1,700/child) pays out as a cash refund",
    ],
    "nslp": [
        "Complete the school meals application at your child's school at the start of the year",
        "Benefits apply immediately after approval and cover breakfast and lunch",
        "Free meals for households under 130% FPL; reduced price ($0.40/meal) up to 185% FPL",
    ],
    "ccdf": [
        "Contact your state child care agency at childcare.gov",
        "Gather proof of work or school enrollment, income, and your child's information",
        "Waitlists are common — apply as soon as possible",
    ],
    "medicare_savings": [
        "Apply through your state Medicaid office",
        "Contact your State Health Insurance Assistance Program (SHIP) for free counseling",
        "Bring your Medicare card, proof of income, and photo ID",
    ],
}


def _get_next_steps(program_id: str) -> list[str]:
    """Return static next-steps for a program, normalising state variants."""
    base = program_id
    for token in ("snap", "medicaid", "medi_cal", "tanf"):
        if token in base:
            base = token
            break
    return _NEXT_STEPS.get(base, [
        "Call 211 to speak with a local benefits specialist",
        "Visit benefits.gov to search for additional programs",
        "Contact your county social services office for in-person help",
    ])


def _load_state_metadata() -> dict:
    global _state_metadata_cache
    if _state_metadata_cache is None:
        try:
            with open(STATE_METADATA_PATH) as f:
                _state_metadata_cache = json.load(f).get("states", {})
        except FileNotFoundError:
            _state_metadata_cache = {}
    return _state_metadata_cache


def _state_context_note(state: str | None) -> str:
    if not state:
        return ""
    meta = _load_state_metadata().get(state.strip().upper())
    if not meta:
        return ""
    expanded = meta.get("medicaid_expansion", True)
    tanf_max = meta.get("tanf_max_monthly_family3")
    state_name = meta.get("name", state)
    lines: list[str] = [f"State context for {state_name}:"]
    if expanded:
        lines.append("- Medicaid IS expanded: adults up to 138% FPL qualify for Medicaid.")
    else:
        lines.append(
            "- Medicaid is NOT expanded: working-age adults without children generally do NOT qualify "
            "for Medicaid in this state unless disabled or elderly."
        )
    if tanf_max:
        lines.append(f"- Maximum TANF benefit for a family of 3 in this state: ~${tanf_max}/month.")
    return "\n".join(lines)


# ── Pre-computation helpers for the simplified Ollama prompt ─────────────────

def _snap_benefit_estimate(monthly_income: float, household_size: int) -> int:
    # FY2025 (Oct 2024–Sep 2025) USDA maximum monthly allotments — 48 states + DC
    snap_maxes = {1: 292, 2: 536, 3: 768, 4: 975, 5: 1158, 6: 1390, 7: 1536, 8: 1756}
    # FY2025 standard deductions (used in net income calculation)
    std_deductions = {1: 204, 2: 204, 3: 204, 4: 215, 5: 252, 6: 289, 7: 289, 8: 289}
    hs = min(household_size, 8)
    net = max(0.0, monthly_income * 0.8 - std_deductions.get(hs, 289))
    return max(23, round(snap_maxes.get(hs, 1756) - net * 0.30))


def _program_eligibility_note(
    program: dict,
    profile: UserProfile,
    fpl_pct: float,
    annual_income: float,
    household_size: int,
    state_meta: dict | None,
) -> str:
    """
    Return a compact, pre-computed eligibility note for one program.
    All comparisons (income vs FPL limit, demographic checks) are computed here
    so Gemma only needs to confirm and write a reason — not derive answers from rules.
    """
    pid = program["id"]
    name = program["name"]
    rules = program.get("eligibility_rules", {})
    income_rules = rules.get("income", {})
    expanded = state_meta.get("medicaid_expansion", True) if state_meta else True
    monthly_income = annual_income / 12
    kids = profile.children or 0

    parts: list[str] = [name]

    # Income vs limit comparison — pre-computed
    limit_pct = (
        income_rules.get("limit_pct_of_fpl")
        or income_rules.get("adults_limit_pct_of_fpl")
    )
    if limit_pct:
        direction = "UNDER" if fpl_pct <= float(limit_pct) else "OVER"
        parts.append(f"income {fpl_pct:.0f}% FPL vs {limit_pct}% FPL limit → {direction}")

    # Program-specific pre-computed facts
    if "snap" in pid or "calfresh" in pid:
        if fpl_pct <= 130:
            est = _snap_benefit_estimate(monthly_income, household_size)
            parts.append(f"eligible; estimated monthly benefit ~${est}")
        else:
            parts.append("income exceeds 130% FPL limit; not eligible")

    elif "medicaid" in pid or "medi_cal" in pid:
        eligible_reasons: list[str] = []
        if kids > 0 and fpl_pct <= 200:
            eligible_reasons.append(f"{kids} children qualify at 200% FPL")
        if profile.has_pregnant and fpl_pct <= 200:
            eligible_reasons.append("pregnant member qualifies at 200% FPL")
        if expanded and fpl_pct <= 138:
            eligible_reasons.append("adults qualify (state expanded Medicaid to 138% FPL)")
        if not expanded and not eligible_reasons:
            parts.append(
                "NOT expanded state — working-age adults without children generally do NOT qualify; "
                "only children and pregnant members may be eligible"
            )
        if eligible_reasons:
            parts.append("eligible for: " + "; ".join(eligible_reasons))

    elif pid == "chip":
        chip_limit = state_meta.get("chip_income_limit_pct_fpl", 200) if state_meta else 200
        if kids > 0 and fpl_pct <= chip_limit:
            parts.append(f"{kids} children present; income {fpl_pct:.0f}% FPL under {chip_limit}% limit → eligible")
        else:
            parts.append("no children under 19 or income over limit → not eligible")

    elif pid == "liheap":
        if fpl_pct <= 150:
            priority = bool(profile.has_elderly) or bool(profile.has_children_under_5)
            parts.append("eligible" + ("; household gets priority (elderly or young children present)" if priority else ""))
        else:
            parts.append("income over 150% FPL limit → not eligible")

    elif pid == "wic":
        wic_who = bool(profile.has_pregnant) or bool(profile.has_infant) or bool(profile.has_children_under_5)
        if wic_who and fpl_pct <= 185:
            who = []
            if profile.has_pregnant:
                who.append("pregnant member")
            if profile.has_infant:
                who.append("infant")
            if profile.has_children_under_5:
                who.append("child under 5")
            parts.append(f"eligible for: {', '.join(who)}; income {fpl_pct:.0f}% FPL under 185% limit")
        else:
            parts.append("no pregnant/infant/child-under-5 or income over 185% FPL limit → not eligible")

    elif pid == "ssi":
        if profile.has_disabled and fpl_pct <= 100:
            parts.append("disabled member present; income under limit → likely eligible")
        elif bool(profile.has_elderly) and not profile.has_disabled:
            parts.append(
                "has elderly (60+) member but SSI requires age 65+ or disability; "
                "if under 65 and no disability → not yet eligible; use low confidence"
            )
        else:
            parts.append("no elderly or disabled members → not eligible")

    elif "tanf" in pid:
        tanf_max = state_meta.get("tanf_max_monthly_family3") if state_meta else None
        tanf_limit = 60
        if kids > 0 and fpl_pct <= tanf_limit:
            parts.append(
                f"{kids} children present; income {fpl_pct:.0f}% FPL under {tanf_limit}% typical limit → likely eligible"
                + (f"; state max ~${tanf_max}/month for family of 3" if tanf_max else "")
            )
        else:
            reason = "no children" if kids == 0 else f"income {fpl_pct:.0f}% FPL over {tanf_limit}% typical limit"
            parts.append(f"{reason} → not eligible")

    elif pid == "aca_subsidies":
        medicaid_covers = (
            (expanded and fpl_pct <= 138)
            or (kids > 0 and fpl_pct <= 200)
            or (bool(profile.has_pregnant) and fpl_pct <= 200)
        )
        if medicaid_covers:
            parts.append("household members covered by Medicaid/CHIP → ACA subsidies do not apply")
        elif 100 <= fpl_pct <= 400:
            parts.append(f"income {fpl_pct:.0f}% FPL is in the 100–400% ACA subsidy range → eligible")
        elif fpl_pct < 100 and not expanded:
            parts.append(
                f"income {fpl_pct:.0f}% FPL is below 100% FPL in a non-expansion state → "
                "falls in coverage gap; neither Medicaid nor ACA applies for adults"
            )
        else:
            parts.append("income over 400% FPL → not eligible")

    elif pid == "lifeline":
        if fpl_pct <= 135:
            parts.append(f"income {fpl_pct:.0f}% FPL under 135% limit → eligible; $9.25/month discount")
        else:
            parts.append("income over 135% FPL limit → not eligible")

    elif pid == "housing_choice_voucher":
        if fpl_pct <= 100:
            parts.append(f"income {fpl_pct:.0f}% FPL qualifies; WARNING: 2–10 year waitlists are common")
        else:
            parts.append("income likely over the 50% area-median-income limit → not eligible")

    elif pid == "eitc":
        # 2025 tax year EITC income limits (single/head-of-household filer, IRS Rev. Proc. 2024-40)
        eitc_limits = {0: 19104, 1: 50434, 2: 57310, 3: 61555}
        eitc_limit = eitc_limits.get(min(kids, 3), 61555)
        if profile.employment_status in ("unemployed", "retired"):
            parts.append("EITC requires earned income; household reports no employment → not eligible")
        elif annual_income <= eitc_limit:
            # 2025 tax year maximum EITC (IRS Rev. Proc. 2024-40)
            max_credit = {0: 649, 1: 4328, 2: 7152, 3: 8046}
            est_annual = round(max_credit.get(min(kids, 3), 8046) * 0.75)
            employed = profile.employment_status in ("employed", "part_time", "self_employed")
            conf_note = "if employed" if not employed else ""
            parts.append(
                f"income ${annual_income:,.0f}/yr under ${eitc_limit:,} limit; {kids} children; "
                f"estimated credit ~${est_annual}/year {conf_note}".strip()
            )
        else:
            parts.append(f"income ${annual_income:,.0f}/yr exceeds ${eitc_limit:,} limit → not eligible")

    elif pid == "child_tax_credit":
        if kids > 0 and annual_income <= 200000:
            # 2025 ACTC: min($1,700 × children, 15% × max(0, income − $2,500))
            est_refundable = min(1700 * kids, round(max(0.0, annual_income - 2500) * 0.15))
            parts.append(
                f"{kids} children under 17; income ${annual_income:,.0f}/yr well under $200K phaseout; "
                f"estimated refundable credit ~${est_refundable}/year"
            )
        else:
            parts.append("no children or income over limit → not eligible")

    elif pid == "nslp":
        if kids > 0 and fpl_pct <= 185:
            meal = "free" if fpl_pct <= 130 else "reduced-price ($0.40/meal)"
            parts.append(f"{kids} school-age children; income {fpl_pct:.0f}% FPL → {meal} school meals")
        else:
            parts.append("no children or income over 185% FPL limit → not eligible")

    elif pid == "ccdf":
        if kids > 0 and fpl_pct <= 250:
            parts.append(
                f"{kids} children; income {fpl_pct:.0f}% FPL within typical 200–250% FPL limit; "
                "eligibility depends on parent work/school status"
            )
        else:
            parts.append("no children or income over typical limit → not eligible")

    elif pid == "medicare_savings":
        if profile.has_disabled and fpl_pct <= 135:
            parts.append("disabled member likely on Medicare; income under limit → eligible to have Part B premium covered")
        elif bool(profile.has_elderly) and fpl_pct <= 100:
            parts.append(
                "has elderly (60+) member; if they are 65+ and on Medicare, income qualifies; "
                "use low confidence since we don't know if they've reached 65"
            )
        else:
            parts.append("requires Medicare enrollment (age 65+ or disabled) → not clearly eligible")

    return " | ".join(parts)


def _build_ollama_batch_prompt(
    batch: list[dict],
    profile: UserProfile,
    fpl_pct: float,
    annual_income: float,
    household_size: int,
    state_meta: dict | None,
) -> str:
    """
    Build a simplified eligibility prompt for Gemma on Ollama.
    All income comparisons and demographic checks are pre-computed so Gemma
    does not need to reason from raw rules — it only needs to confirm and explain.
    """
    members: list[str] = []
    if (profile.children or 0) > 0:
        members.append(f"{profile.children} children")
    if profile.has_elderly:
        members.append("elderly adult (60+)")
    if profile.has_pregnant:
        members.append("pregnant adult")
    if profile.has_disabled:
        members.append("disabled member")
    if not members:
        members.append("adults only")

    state_str = profile.state or "unknown state"
    expanded = state_meta.get("medicaid_expansion", True) if state_meta else True
    expansion_note = "" if expanded else f" (Medicaid NOT expanded in {state_str})"

    header = (
        f"Household: {household_size} people, ${annual_income:,.0f}/year income, "
        f"{fpl_pct:.0f}% of Federal Poverty Level, {state_str}{expansion_note}.\n"
        f"Members: {', '.join(members)}.\n\n"
        "Each program below includes pre-computed eligibility facts. "
        "For programs marked eligible, confirm and write one plain-language reason. "
        "For programs marked not eligible, omit them from your response.\n\n"
        "Programs:\n"
    )

    program_lines: list[str] = []
    for p in batch:
        note = _program_eligibility_note(p, profile, fpl_pct, annual_income, household_size, state_meta)
        program_lines.append(f"- {p['id']}: {note}")

    footer = (
        '\n\nReturn a JSON array of eligible programs only. Each item:\n'
        '{"id": "program_id", "eligible": true, "confidence": "high|medium|low", '
        '"reason": "one sentence", "value_usd": number_or_null}\n'
        "No markdown, no explanation, JSON array only."
    )

    return header + "\n".join(program_lines) + footer


async def _run_batch_ollama(
    batch: list[dict],
    profile: UserProfile,
    fpl_pct: float,
    annual_income: float,
    household_size: int,
    state_meta: dict | None,
) -> list[dict]:
    """
    Run one eligibility batch through Gemma on Ollama using the simplified prompt.
    Returns normalized result dicts (program_id, likely_eligible, confidence, reason, value_usd).
    Falls back to an empty list on failure so the caller can use rule-based results instead.
    """
    prompt = _build_ollama_batch_prompt(
        batch, profile, fpl_pct, annual_income, household_size, state_meta
    )

    try:
        response_text = await generate(
            messages=[{"role": "user", "content": prompt}],
            # Minimal system prompt — no "analyst" role that could trigger extended thinking
            system_prompt="Determine benefit eligibility from the pre-computed facts. Return valid JSON only.",
            temperature=0.0,
            json_mode=False,
            # 400 tokens: enough for up to 3 programs × ~80 tokens output + thinking headroom.
            # Keeps each batch under ~40 seconds on Apple Silicon M1 (10 tokens/sec).
            max_tokens=400,
        )
    except Exception as e:
        logger.warning("Ollama batch call failed for %s: %s", [p["id"] for p in batch], e)
        return []

    if not response_text or not response_text.strip():
        logger.warning(
            "Ollama batch returned empty for %s — thinking tokens likely consumed budget; "
            "rule-based fallback will cover these programs",
            [p["id"] for p in batch],
        )
        return []

    raw = safe_parse_json(response_text, fallback=None)
    if not isinstance(raw, list):
        raw = raw.get("results", []) if isinstance(raw, dict) else []

    # Normalise field names (Gemma may use "eligible" instead of "likely_eligible", etc.)
    normalised: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        normalised.append({
            "program_id": item.get("id", item.get("program_id", "")),
            "likely_eligible": item.get("eligible", item.get("likely_eligible", False)),
            "confidence": item.get("confidence", "medium"),
            "reason": item.get("reason", ""),
            "estimated_monthly_value_usd": item.get("value_usd", item.get("estimated_monthly_value_usd")),
        })
    return normalised


# ── Rule-based eligibility (fallback when Gemma fails) ───────────────────────

def _make_result(
    program_id: str,
    program_name: str,
    confidence: str,
    reason: str,
    monthly_value: Optional[float],
    next_steps: list[str],
    value_period: str = "monthly",
) -> dict:
    return {
        "program_id": program_id,
        "program_name": program_name,
        "likely_eligible": True,
        "confidence": confidence,
        "estimated_monthly_value_usd": monthly_value,
        "value_period": value_period,
        "reason": reason,
        "next_steps": next_steps,
    }


def _evaluate_one(
    program: dict,
    profile: UserProfile,
    fpl_pct: float,
    annual_income: float,
    household_size: int,
    state_meta: dict | None,
) -> Optional[dict]:
    """Deterministic rule-based evaluation. Returns a result dict if eligible, else None."""
    pid = program["id"]
    name = program["name"]
    hs = min(household_size, 8)
    monthly_income = annual_income / 12
    has_kids = (profile.children or 0) > 0
    kids = profile.children or 0
    expanded = state_meta.get("medicaid_expansion", True) if state_meta else True

    if "snap" in pid or "calfresh" in pid:
        if fpl_pct > 130:
            return None
        est = float(_snap_benefit_estimate(monthly_income, hs))
        conf = "high" if fpl_pct <= 100 else "medium"
        return _make_result(
            pid, name, conf,
            f"Your household income ({fpl_pct:.0f}% FPL) is within SNAP's 130% limit.",
            est, _get_next_steps(pid),
        )

    if "medicaid" in pid or "medi_cal" in pid:
        children_ok = has_kids and fpl_pct <= 200
        pregnant_ok = bool(profile.has_pregnant) and fpl_pct <= 200
        adults_ok = expanded and fpl_pct <= 138
        elderly_disabled_ok = (bool(profile.has_elderly) or bool(profile.has_disabled)) and fpl_pct <= 88
        if not any([children_ok, pregnant_ok, adults_ok, elderly_disabled_ok]):
            return None
        reasons: list[str] = []
        if children_ok:
            reasons.append("children qualify")
        if pregnant_ok:
            reasons.append("pregnancy qualifies")
        if adults_ok:
            reasons.append("adults qualify in this expansion state")
        if elderly_disabled_ok:
            reasons.append("elderly or disabled members may qualify")
        conf = "high" if (children_ok or pregnant_ok) else "medium"
        return _make_result(
            pid, name, conf,
            f"Medicaid applies because {' and '.join(reasons)} — income {fpl_pct:.0f}% FPL is within the limit.",
            None, _get_next_steps(pid),
        )

    if pid == "chip":
        chip_limit = state_meta.get("chip_income_limit_pct_fpl", 200) if state_meta else 200
        if not has_kids or fpl_pct > chip_limit:
            return None
        return _make_result(
            pid, name, "high" if fpl_pct <= 150 else "medium",
            f"Your children qualify — income ({fpl_pct:.0f}% FPL) is within the {chip_limit}% FPL limit.",
            None, _get_next_steps(pid),
        )

    if pid == "liheap":
        if fpl_pct > 150:
            return None
        priority = bool(profile.has_elderly) or bool(profile.has_children_under_5)
        reason = f"Income ({fpl_pct:.0f}% FPL) qualifies for energy assistance."
        if priority:
            reason += " Elderly members or young children get priority."
        return _make_result(pid, name, "high" if fpl_pct <= 100 else "medium", reason, 42.0, _get_next_steps(pid), value_period="seasonal")

    if pid == "wic":
        wic_who = bool(profile.has_pregnant) or bool(profile.has_infant) or bool(profile.has_children_under_5)
        if not wic_who or fpl_pct > 185:
            return None
        who = [x for x in ["pregnant member", "infant", "child under 5"]
               if (x == "pregnant member" and profile.has_pregnant)
               or (x == "infant" and profile.has_infant)
               or (x == "child under 5" and profile.has_children_under_5)]
        qualifying_count = len(who)
        return _make_result(
            pid, name, "high",
            f"WIC covers {', '.join(who)} — income ({fpl_pct:.0f}% FPL) is within the 185% FPL limit.",
            50.0 * max(qualifying_count, 1), _get_next_steps(pid),
        )

    if pid == "ssi":
        if profile.has_disabled and fpl_pct <= 100:
            return _make_result(pid, name, "medium",
                "Disabled household members may qualify for SSI monthly cash.", 967.0, _get_next_steps(pid))
        if bool(profile.has_elderly) and not profile.has_disabled and fpl_pct <= 75:
            return _make_result(pid, name, "low",
                "SSI provides cash for people 65+ or disabled. If household members have reached 65, they may qualify.",
                967.0, _get_next_steps(pid))
        return None

    if "tanf" in pid:
        if not has_kids or fpl_pct > 60:
            return None
        tanf_max = state_meta.get("tanf_max_monthly_family3") if state_meta else None
        return _make_result(
            pid, name, "high" if fpl_pct <= 40 else "medium",
            f"TANF provides temporary cash for families with children — income ({fpl_pct:.0f}% FPL) is within the typical limit.",
            float(tanf_max) if tanf_max else 350.0, _get_next_steps(pid),
        )

    if pid == "aca_subsidies":
        medicaid_eligible = (expanded and fpl_pct <= 138) or (has_kids and fpl_pct <= 200) or (bool(profile.has_pregnant) and fpl_pct <= 200)
        if medicaid_eligible or fpl_pct < 100 or fpl_pct > 400:
            return None
        return _make_result(
            pid, name, "high" if fpl_pct <= 200 else "medium",
            f"Income ({fpl_pct:.0f}% FPL) qualifies for ACA premium tax credits.",
            300.0, _get_next_steps(pid),
        )

    if pid == "lifeline":
        if fpl_pct > 135:
            return None
        return _make_result(pid, name, "high",
            f"Income ({fpl_pct:.0f}% FPL) qualifies for the Lifeline phone/internet discount.", 9.25, _get_next_steps(pid))

    if pid == "housing_choice_voucher":
        if fpl_pct > 100:
            return None
        return _make_result(pid, name, "low",
            f"Income ({fpl_pct:.0f}% FPL) is in range for Section 8 — but most areas have 2–10 year waitlists.",
            800.0, _get_next_steps(pid))

    if pid == "eitc":
        no_earned = profile.employment_status in ("unemployed", "retired")
        if no_earned:
            return None
        # 2025 tax year income limits (single/HoH filer — IRS Rev. Proc. 2024-40)
        eitc_limits = {0: 19104, 1: 50434, 2: 57310, 3: 61555}
        if annual_income > eitc_limits.get(min(kids, 3), 61555):
            return None
        # 2025 tax year maximum credits; ~75% accounts for typical phaseout at moderate incomes
        max_credit = {0: 649, 1: 4328, 2: 7152, 3: 8046}
        estimate = round(max_credit.get(min(kids, 3), 8046) * 0.75 / 12, 0)
        return _make_result(
            pid, name, "high" if kids >= 2 else "medium",
            f"EITC gives working families a significant tax refund — {kids} children and income around ${annual_income:,.0f}/year qualifies.",
            estimate, _get_next_steps(pid), value_period="annual",
        )

    if pid == "child_tax_credit":
        if kids == 0 or annual_income > 200000:
            return None
        # ACTC 2025: refundable portion = min($1,700 × children, 15% × max(0, earned_income − $2,500))
        # IRS Rev. Proc. 2024-40; phaseout starts at $200K single / $400K married
        actc = min(1700 * kids, round(max(0.0, annual_income - 2500) * 0.15))
        if actc == 0:
            return None  # Too little income to unlock any refundable credit
        return _make_result(
            pid, name, "high" if annual_income <= 50000 else "medium",
            f"With {kids} child{'ren' if kids != 1 else ''} and income around ${annual_income:,.0f}/year, you qualify for the Child Tax Credit.",
            round(actc / 12, 0), _get_next_steps(pid), value_period="annual",
        )

    if pid == "nslp":
        if not has_kids or fpl_pct > 185:
            return None
        free = fpl_pct <= 130
        # SY2024-25 USDA reimbursement: free lunch ~$3.40/meal; reduced-price students pay $0.40
        # so the net savings for reduced-price families is ~$2.99/meal (full rate minus student payment)
        per_meal = 3.40 if free else 2.99
        return _make_result(
            pid, name, "high" if free else "medium",
            f"School-age children qualify for {'free' if free else 'reduced-price'} school meals — income {fpl_pct:.0f}% FPL.",
            round(per_meal * 20 * max(kids, 1), 0), _get_next_steps(pid),
        )

    if pid == "ccdf":
        if kids == 0 or fpl_pct > 250:
            return None
        return _make_result(pid, name, "medium",
            f"Child care subsidies may be available — income ({fpl_pct:.0f}% FPL) is within typical limits.",
            400.0, _get_next_steps(pid))

    if pid == "medicare_savings":
        if profile.has_disabled and fpl_pct <= 135:
            return _make_result(pid, name, "medium",
                "Disabled Medicare-enrolled members can have Part B premiums covered.", 185.0, _get_next_steps(pid))
        if bool(profile.has_elderly) and fpl_pct <= 100:
            return _make_result(pid, name, "low",
                "Medicare Savings covers Part B premiums for members 65+ enrolled in Medicare.", 185.0, _get_next_steps(pid))
        return None

    return None


def _rule_based_eligibility_check(
    programs: list[dict],
    profile: UserProfile,
    fpl_pct: float,
    annual_income: float,
    household_size: int,
    state_meta: dict | None = None,
) -> list[dict]:
    results = []
    for program in programs:
        result = _evaluate_one(program, profile, fpl_pct, annual_income, household_size, state_meta)
        if result:
            results.append(result)
    return results


# ── Gemma batch eligibility (Gemini API path) ────────────────────────────────

ELIGIBILITY_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "program_id": {"type": "string"},
                    "program_name": {"type": "string"},
                    "likely_eligible": {"type": "boolean"},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                    "estimated_monthly_value_usd": {"type": "number"},
                    "reason": {"type": "string"},
                    "next_steps": {"type": "array", "items": {"type": "string"}},
                    "apply_url": {"type": "string"},
                },
                "required": ["program_id", "program_name", "likely_eligible", "confidence", "reason", "next_steps"],
            },
        },
        "total_estimated_monthly_usd": {"type": "number"},
        "disclaimer": {"type": "string"},
    },
    "required": ["results", "total_estimated_monthly_usd", "disclaimer"],
}

EXTRACT_PROFILE_FUNCTION = {
    "name": "extract_user_profile",
    "description": "Extract structured information about the user's household situation.",
    "parameters": {
        "type": "object",
        "properties": {
            "household_size": {"type": "integer"},
            "adults": {"type": "integer"},
            "children": {"type": "integer"},
            "monthly_income_usd": {"type": "number"},
            "state": {"type": "string"},
            "has_elderly": {"type": "boolean"},
            "has_disabled": {"type": "boolean"},
            "has_pregnant": {"type": "boolean"},
            "has_infant": {"type": "boolean"},
            "has_children_under_5": {"type": "boolean"},
            "citizenship_status": {"type": "string", "enum": ["citizen", "permanent_resident", "other", "unknown"]},
            "employment_status": {"type": "string", "enum": ["employed", "unemployed", "part_time", "self_employed", "retired", "unknown"]},
            "has_health_insurance": {"type": "boolean"},
            "housing_status": {"type": "string", "enum": ["renter", "owner", "homeless", "other", "unknown"]},
            "veteran": {"type": "boolean"},
            "profile_complete": {"type": "boolean"},
        },
        "required": ["profile_complete"],
    },
}


def _categorical_prefilter(profile: UserProfile, programs: List[dict]) -> List[dict]:
    """
    Remove programs the household definitively cannot qualify for.
    None = unknown = keep (Gemma or rule-based decides). Only removes when
    the relevant field is explicitly False or 0.
    """
    no_children = profile.children is not None and profile.children == 0
    no_wic_demographics = (
        profile.has_pregnant is False
        and profile.has_infant is False
        and profile.has_children_under_5 is False
        and no_children
    )
    no_elderly_or_disabled = profile.has_elderly is False and profile.has_disabled is False

    filtered: List[dict] = []
    for program in programs:
        pid = program.get("id", "")
        if pid == "wic" and no_wic_demographics:
            continue
        if pid in ("chip", "nslp", "ccdf") and no_children:
            continue
        if "tanf" in pid and no_children:
            continue
        if pid in ("ssi", "medicare_savings") and no_elderly_or_disabled:
            continue
        filtered.append(program)

    removed = len(programs) - len(filtered)
    if removed:
        logger.info("Categorical pre-filter removed %d programs based on confirmed demographics", removed)
    return filtered


def _compact_profile_json(profile: UserProfile) -> str:
    data = {k: v for k, v in profile.model_dump().items() if v is not None}
    return json.dumps(data, indent=2)


def _slim_program_for_prompt(program: dict) -> dict:
    rules = program.get("eligibility_rules", {})
    income = rules.get("income", {})
    slim_income = {k: v for k, v in income.items()
                   if k in ("limit_pct_of_fpl", "adults_limit_pct_of_fpl", "children_limit_pct_of_fpl",
                             "pregnant_limit_pct_of_fpl", "min_pct_of_fpl", "max_pct_of_fpl", "note")}
    slim_rules: dict = {}
    if slim_income:
        slim_rules["income"] = slim_income
    for key in ("who", "who_qualifies", "age", "priority", "categorical_eligibility",
                "expansion_states", "not_eligible_if", "citizenship", "time_limit"):
        if key in rules:
            slim_rules[key] = rules[key]
    return {
        "id": program["id"],
        "name": program["name"],
        "description": program["description"],
        "monthly_benefit_range": program.get("monthly_benefit_range", {}),
        "eligibility_rules": slim_rules,
    }


async def _run_batch_eligibility(
    batch: List[dict],
    profile: UserProfile,
    household_size: int,
    fpl_amount: int,
    annual_income: float,
    fpl_pct: float,
    prompt_template: str,
    state_context: str = "",
) -> List[dict]:
    """Gemma batch reasoning — used on Gemini API path only."""
    prompt = prompt_template.format(
        profile_json=_compact_profile_json(profile),
        household_size=household_size,
        fpl_amount=f"{fpl_amount:,}",
        annual_income=f"{annual_income:,.0f}",
        fpl_pct=f"{fpl_pct:.0f}",
        programs_json=json.dumps([_slim_program_for_prompt(p) for p in batch], indent=2),
    )
    system_prompt = (
        "You are a precise benefits eligibility analyst. "
        "Return ONLY a valid JSON object. No markdown, no prose, no code fences."
    )
    if state_context:
        system_prompt = f"{state_context}\n\n{system_prompt}"

    try:
        response_text = await generate(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=system_prompt,
            temperature=0.1,
            json_mode=False,
            max_tokens=700,
        )
    except Exception as e:
        logger.warning("Batch eligibility Gemma call failed for %s: %s", [p["id"] for p in batch], e)
        return []

    raw = safe_parse_json(response_text, fallback=None)
    if raw is None:
        logger.warning("Batch eligibility: failed to parse Gemma JSON for %s", [p["id"] for p in batch])
        return []
    return raw if isinstance(raw, list) else raw.get("results", [])


def _state_replaces_federal(programs: List[dict]) -> set[str]:
    replaced: set[str] = set()
    for program in programs:
        pid = program.get("id", "").lower()
        category = program.get("category", "").lower()
        tags = {str(t).lower() for t in program.get("tags", [])}
        if "snap" in pid or ("food" == category and "state" in tags):
            replaced.add("snap")
        if "medicaid" in pid or "medi_cal" in pid:
            replaced.add("medicaid")
        if "tanf" in pid:
            replaced.add("tanf")
    return replaced


def load_programs(state: str | None = None) -> List[dict]:
    with open(FEDERAL_BENEFITS_PATH) as f:
        federal_programs = json.load(f)["programs"]
    if not state:
        return federal_programs
    state_code = state.strip().upper()
    state_path = os.path.join(STATE_PROGRAMS_DIR, f"{state_code}.json")
    if not os.path.exists(state_path):
        logger.info("No state benefits file for %s; using federal programs only", state_code)
        return federal_programs
    with open(state_path) as f:
        state_programs = json.load(f).get("programs", [])
    replaced = _state_replaces_federal(state_programs)
    merged = [p for p in federal_programs if p.get("id") not in replaced]
    merged.extend(state_programs)
    logger.info("Loaded %d federal + %d state programs for %s",
                len(merged) - len(state_programs), len(state_programs), state_code)
    return merged


def _program_apply_url(program_id: str) -> str | None:
    urls = {
        # Federal
        "snap": "https://www.fns.usda.gov/snap/state-directory",
        "medicaid": "https://www.healthcare.gov/medicaid-chip/",
        "chip": "https://www.insurekidsnow.gov/",
        "liheap": "https://www.acf.hhs.gov/ocs/map/liheap-map-state-and-territory-contact-listing",
        "wic": "https://www.fns.usda.gov/wic/program-contacts",
        "ssi": "https://www.ssa.gov/ssi/",
        "tanf": "https://www.acf.hhs.gov/ofa/map/about/help-families",
        # AZ
        "az_snap": "https://des.az.gov/services/basic-needs/food/nutrition-assistance",
        "az_medicaid": "https://healthearizonaplus.gov/",
        "az_tanf": "https://des.az.gov/services/financial/cash-assistance-tpp",
        # CA
        "calfresh": "https://www.getcalfresh.org/",
        "medi_cal": "https://www.coveredca.com/",
        "ca_eitc": "https://www.ftb.ca.gov/file/personal/credits/california-earned-income-tax-credit.html",
        # FL
        "fl_snap": "https://www.myflfamilies.com/services/public-assistance",
        "fl_medicaid": "https://www.myflfamilies.com/services/public-assistance",
        # GA
        "ga_snap": "https://gateway.ga.gov/",
        "ga_medicaid": "https://medicaid.georgia.gov/",
        "ga_tanf": "https://dfcs.georgia.gov/tanf",
        # IL
        "il_snap": "https://abe.illinois.gov/",
        "il_medicaid": "https://abe.illinois.gov/",
        "il_tanf": "https://abe.illinois.gov/",
        # MI
        "mi_snap": "https://mibridges.michigan.gov/",
        "mi_medicaid": "https://mibridges.michigan.gov/",
        "mi_tanf": "https://mibridges.michigan.gov/",
        # NC
        "nc_snap": "https://www.epass.nc.gov/",
        "nc_medicaid": "https://medicaid.ncdhhs.gov/",
        "nc_tanf": "https://www.ncdhhs.gov/divisions/dss/wf",
        # NJ
        "nj_snap": "https://www.nj.gov/humanservices/dfd/programs/njsnap/",
        "nj_medicaid": "https://www.nj.gov/humanservices/dmahs/home/",
        "nj_tanf": "https://www.nj.gov/humanservices/dfd/programs/workfirst/",
        # NY
        "ny_snap": "https://mybenefits.ny.gov/",
        "ny_medicaid": "https://nystateofhealth.ny.gov/",
        # OH
        "oh_snap": "https://benefits.ohio.gov/",
        "oh_medicaid": "https://medicaid.ohio.gov/",
        "oh_tanf": "https://jfs.ohio.gov/",
        # PA
        "pa_snap": "https://www.compass.state.pa.us/",
        "pa_medicaid": "https://www.compass.state.pa.us/",
        "pa_tanf": "https://www.compass.state.pa.us/",
        # TX
        "tx_snap": "https://www.yourtexasbenefits.com/",
        "tx_medicaid": "https://www.yourtexasbenefits.com/",
        "tx_tanf": "https://www.yourtexasbenefits.com/",
        # VA
        "va_snap": "https://www.commonhelp.virginia.gov/",
        "va_medicaid": "https://www.commonhelp.virginia.gov/",
        "va_tanf": "https://www.commonhelp.virginia.gov/",
        # WA
        "wa_snap": "https://www.washingtonconnection.org/",
        "wa_medicaid": "https://www.wahealthplanfinder.org/",
        "wa_tanf": "https://www.dshs.wa.gov/esa/community-services-offices",
        # Remaining federal
        "aca_subsidies": "https://www.healthcare.gov/",
        "lifeline": "https://www.lifelinesupport.org/",
        "housing_choice_voucher": "https://www.hud.gov/program_offices/public_indian_housing/pha/contacts",
        "eitc": "https://www.irs.gov/credits-deductions/individuals/earned-income-tax-credit/free-tax-return-preparation-for-you-by-volunteers",
        "child_tax_credit": "https://www.irs.gov/credits-deductions/individuals/child-tax-credit",
        "nslp": "https://www.fns.usda.gov/nslp",
        "ccdf": "https://childcare.gov/",
        "medicare_savings": "https://www.medicare.gov/basics/costs/help/medicare-savings-programs",
    }
    return urls.get(program_id)


def _static_monthly_estimate(program: dict, profile: UserProfile) -> float | None:
    benefit_range = program.get("monthly_benefit_range", {})
    category = program.get("category")
    if benefit_range.get("typical_usd") is not None:
        value = float(benefit_range["typical_usd"])
        return round(value / 12, 2) if "seasonal" in program.get("tags", []) else value
    if benefit_range.get("typical_family_4_usd") is not None:
        return round(float(benefit_range["typical_family_4_usd"]) * min(profile.household_size or 1, 4) / 4, 2)
    min_v = benefit_range.get("min_usd")
    max_v = benefit_range.get("max_usd")
    if min_v is None or max_v is None:
        return None
    min_v, max_v = float(min_v), float(max_v)
    if max_v <= 0 or category == "healthcare":
        return None
    if "annual" in program.get("tags", []) or "seasonal" in program.get("tags", []):
        return round(max_v / 12, 2)
    return round((min_v + max_v) * 0.35, 2)


async def run_eligibility_check(
    profile: UserProfile,
    language: str = "en",
) -> EligibilityResponse:
    """
    Run eligibility check against the benefits database.

    Ollama path — Gemma with pre-computed simplified prompts (sequential batches),
    falling back to rule-based for any batch Gemma cannot process.

    Gemini API path — full Gemma batch reasoning in parallel.
    """
    from config import settings as _settings
    is_ollama = _settings.model_backend == "ollama"

    all_programs = load_programs(profile.state)
    all_programs = _categorical_prefilter(profile, all_programs)

    if not all_programs:
        return EligibilityResponse(
            results=[], total_estimated_monthly_usd=0,
            disclaimer="No matching programs found. Please consult 211 for local assistance.",
        )

    household_size = profile.household_size or 1
    annual_income = (
        (profile.monthly_income_usd or 0) * 12
        if profile.annual_income_usd is None
        else (profile.annual_income_usd or 0)
    )
    fpl_amount = get_fpl(household_size)
    fpl_pct = get_fpl_percentage(annual_income, household_size)

    state_meta: dict | None = None
    if profile.state:
        state_meta = _load_state_metadata().get(profile.state.strip().upper())

    batches = [all_programs[i: i + BATCH_SIZE] for i in range(0, len(all_programs), BATCH_SIZE)]

    if is_ollama:
        # Pre-compute rule-based results for every program — used as fallback and for next_steps
        rule_by_pid: dict[str, dict] = {}
        for result in _rule_based_eligibility_check(all_programs, profile, fpl_pct, annual_income, household_size, state_meta):
            rule_by_pid[result["program_id"]] = result

        logger.info(
            "Ollama path: %d programs in %d batch(es); Gemma with pre-computed prompts + rule-based fallback",
            len(all_programs), len(batches),
        )

        # Run Gemma batches sequentially — each gets its own full timeout window
        gemma_by_pid: dict[str, dict] = {}
        for i, batch in enumerate(batches):
            logger.info("Batch %d/%d — %s", i + 1, len(batches), [p["id"] for p in batch])
            gemma_results = await _run_batch_ollama(
                batch, profile, fpl_pct, annual_income, household_size, state_meta
            )
            for r in gemma_results:
                pid = r.get("program_id", "")
                if pid:
                    gemma_by_pid[pid] = r

        # Merge: Gemma provides eligibility decision + reason; rule-based provides next_steps + estimate
        all_raw_results: list[dict] = []
        gemma_covered = set(gemma_by_pid.keys())
        rule_covered = set(rule_by_pid.keys())

        for program in all_programs:
            pid = program["id"]
            if pid in gemma_covered:
                g = gemma_by_pid[pid]
                if not g.get("likely_eligible"):
                    continue  # Gemma said not eligible
                # Use Gemma's decision + reason, rule-based next_steps and estimate
                rb = rule_by_pid.get(pid, {})
                all_raw_results.append({
                    "program_id": pid,
                    "program_name": program["name"],
                    "likely_eligible": True,
                    "confidence": g.get("confidence", "medium"),
                    "reason": g.get("reason", rb.get("reason", "")),
                    # Always use rule-based estimate — Gemma returns annual/seasonal
                    # amounts as raw numbers without a period indicator, which causes
                    # the frontend to treat them as monthly and wildly overstate totals.
                    "estimated_monthly_value_usd": rb.get("estimated_monthly_value_usd"),
                    "value_period": rb.get("value_period", "monthly"),
                    "next_steps": rb.get("next_steps") or _get_next_steps(pid),
                })
            elif pid in rule_covered:
                # Gemma didn't cover this program — use full rule-based result
                logger.info("Using rule-based fallback for %s (not returned by Gemma)", pid)
                all_raw_results.append(rule_by_pid[pid])

    else:
        # Gemini API: full Gemma reasoning in parallel
        state_context = _state_context_note(profile.state)
        if state_context:
            logger.info("Injecting state context for %s into Gemma system prompt", profile.state)

        prompt_path = os.path.join(os.path.dirname(__file__), "../data/prompts/eligibility_prompt.txt")
        with open(prompt_path) as f:
            prompt_template = f.read()

        logger.info(
            "Gemini API: %d programs in %d batch(es), running in parallel",
            len(all_programs), len(batches),
        )
        batch_kwargs = dict(
            profile=profile, household_size=household_size, fpl_amount=fpl_amount,
            annual_income=annual_income, fpl_pct=fpl_pct,
            prompt_template=prompt_template, state_context=state_context,
        )
        batch_results_list = await asyncio.gather(
            *[_run_batch_eligibility(batch=batch, **batch_kwargs) for batch in batches]
        )
        all_raw_results = [item for results in batch_results_list for item in results]

    if not all_raw_results:
        return EligibilityResponse(
            results=[], total_estimated_monthly_usd=0,
            disclaimer="No matching programs found. Please consult 211 for local assistance or visit benefits.gov.",
        )

    try:
        results: List[EligibilityResult] = []
        total = 0.0
        for item in all_raw_results:
            if not item.get("likely_eligible"):
                continue
            program_data = next((p for p in all_programs if p["id"] == item.get("program_id")), {})
            item["required_documents"] = program_data.get("required_documents", item.get("required_documents", []))
            if not item.get("apply_url"):
                item["apply_url"] = _program_apply_url(item.get("program_id", ""))
            if program_data.get("category"):
                item["category"] = program_data["category"]
            if item.get("estimated_monthly_value_usd") is None and program_data:
                item["estimated_monthly_value_usd"] = _static_monthly_estimate(program_data, profile)
            item.setdefault("next_steps", _get_next_steps(item.get("program_id", "")))
            item.setdefault("reason", "Based on the information provided, you may qualify.")
            item.setdefault("required_documents", [])
            result = EligibilityResult(**item)
            results.append(result)
            # Only count recurring monthly benefits in the total — annual/seasonal
            # programs (EITC, CTC, LIHEAP) are stored as monthly equivalents but
            # paid as lump sums; including them would overstate the monthly figure.
            if result.estimated_monthly_value_usd and (result.value_period or "monthly") == "monthly":
                total += result.estimated_monthly_value_usd

        results.sort(key=lambda x: x.estimated_monthly_value_usd or 0, reverse=True)
        logger.info("Eligibility check complete: %d qualifying programs, total $%.0f/mo", len(results), total)
        return EligibilityResponse(results=results, total_estimated_monthly_usd=total)

    except Exception as e:
        logger.error("Eligibility check: error building results: %s", e)
        return EligibilityResponse(
            results=[], total_estimated_monthly_usd=0,
            disclaimer="Eligibility data could not be validated. Please retry.",
        )
