"""
Main conversational endpoint.
Gemma extracts the structured profile first, then Gemma runs eligibility.
Code is responsible for validation, JSON repair, and response shaping.
"""

import json
import logging
import os

from fastapi import APIRouter
from models.schemas import ChatRequest, ChatResponse, UserProfile
from services.eligibility_engine import run_eligibility_check
from services.gemma import generate
from utils.formatting import safe_parse_json

logger = logging.getLogger(__name__)
router = APIRouter()

LANG_MAP = {
    "es": "Spanish",
    "zh": "Chinese",
    "vi": "Vietnamese",
    "ar": "Arabic",
    "fr": "French",
    "pt": "Portuguese",
    "ko": "Korean",
    "ru": "Russian",
}

PROFILE_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "household_size": {"type": "integer"},
        "adults": {"type": "integer"},
        "children": {"type": "integer"},
        "monthly_income_usd": {"type": "number"},
        "annual_income_usd": {"type": "number"},
        "state": {"type": "string"},
        "zip_code": {"type": "string"},
        "has_elderly": {"type": "boolean"},
        "has_disabled": {"type": "boolean"},
        "has_pregnant": {"type": "boolean"},
        "has_infant": {"type": "boolean"},
        "has_children_under_5": {"type": "boolean"},
        "citizenship_status": {"type": "string"},
        "employment_status": {"type": "string"},
        "has_health_insurance": {"type": "boolean"},
        "housing_status": {"type": "string"},
        "utility_bills": {"type": "boolean"},
        "is_student": {"type": "boolean"},
        "veteran": {"type": "boolean"},
        "currently_on_snap": {"type": "boolean"},
        "currently_on_medicaid": {"type": "boolean"},
        "profile_complete": {"type": "boolean"},
    },
    "required": ["profile_complete"],
}


def _load_prompt(filename: str) -> str:
    path = os.path.join(os.path.dirname(__file__), f"../data/prompts/{filename}")
    with open(path) as f:
        return f.read()


def _build_conversation_text(messages: list[dict]) -> str:
    return "\n".join(f"{msg['role'].upper()}: {msg['content']}" for msg in messages)


def _missing_profile_fields(profile: UserProfile) -> list[str]:
    """
    Return fields still needed before running eligibility.
    After collecting state, household size, and income, we ask ONE combined
    demographics question that covers children (with ages), elderly/senior
    citizens, disability, and pregnancy — instead of chaining separate questions.
    If the user already mentioned any of this in an earlier message, extraction
    populates those fields and we skip to whichever piece is still missing.
    """
    missing = []
    if profile.state is None:
        missing.append("state")
        return missing
    if profile.household_size is None:
        missing.append("household_size")
        return missing
    if profile.monthly_income_usd is None and profile.annual_income_usd is None:
        missing.append("monthly_income")
        return missing

    need_children = profile.household_size > 1 and profile.children is None
    need_elderly_disabled = profile.has_elderly is None and profile.has_disabled is None

    if need_children and need_elderly_disabled:
        # Neither children nor elderly/disability info collected yet.
        # Ask ONE comprehensive question that covers all household member details.
        missing.append("demographics")
        return missing
    if need_children:
        missing.append("children")
        return missing
    if need_elderly_disabled:
        missing.append("elderly_disabled")
        return missing
    return missing


def _model_unavailable_reply(language: str) -> str:
    if language == "es":
        return (
            "Parece que el modelo no está disponible en este momento. "
            "Por favor intenta de nuevo e incluye tu estado, tamaño del hogar e ingreso mensual en tu mensaje."
        )
    return (
        "It looks like the model isn't available right now. "
        "Please try again and include your state, household size, and monthly income in your message."
    )


def _next_question(profile: UserProfile, language: str) -> str:
    """
    Return the next question to ask the user based on what's missing.
    Deterministic — no Gemma call needed. Gemma4's 150-token thinking budget
    consistently consumes all tokens before generating visible output.
    """
    missing = _missing_profile_fields(profile)
    if not missing:
        return "I think I have enough to check what you may qualify for. Let me look that up for you."
    return _fallback_question(missing[0], language)


def _fallback_question(field: str, language: str) -> str:
    if language == "es":
        questions = {
            "state": "¿En qué estado vives?",
            "household_size": "¿Cuántas personas viven en tu hogar en total, incluyéndote a ti?",
            "monthly_income": (
                "¿Aproximadamente cuánto dinero entra al hogar cada mes antes de impuestos? "
                "Un estimado está bien."
            ),
            "demographics": (
                "Para encontrar los programas correctos, cuéntame sobre las personas en tu hogar: "
                "¿hay niños y qué edades tienen? ¿Alguien tiene 60 años o más, vive con una discapacidad "
                "o está embarazada? Si no mencionas nada sobre alguien, asumiré que es un adulto sano. "
                "Di 'No' si ninguno de esos casos aplica."
            ),
            "children": (
                "¿Hay niños menores de 18 años en tu hogar? Si es así, ¿cuántos y qué edades tienen?"
            ),
            "elderly_disabled": (
                "¿Alguien en tu hogar tiene 60 años o más, vive con una discapacidad o está embarazada? "
                "Di 'No' si ninguno aplica."
            ),
        }
        return questions.get(field, "Necesito un dato más para revisar posibles beneficios.")
    questions = {
        "state": "What state do you live in?",
        "household_size": "How many people are in your household in total, including yourself?",
        "monthly_income": (
            "About how much money comes into the household each month before taxes? "
            "A rough estimate is fine."
        ),
        "demographics": (
            "To find the right programs, tell me about the people in your household. "
            "Are there any children and how old are they? Is anyone 60 or older, "
            "living with a disability, or pregnant? "
            "If you don't mention something about someone, I'll assume they're a healthy adult."
            "Please just say 'No' if none of those apply."
        ),
        "children": (
            "Are there any children under 18 in your household? "
            "If yes, how many and what are their ages?"
        ),
        "elderly_disabled": (
            "Is anyone in your household 60 or older, living with a disability, or currently pregnant? "
            "Just say 'No' if none of those apply."
        ),
    }
    return questions.get(field, "I need one more detail before I can check likely benefits.")


def _build_eligibility_reply(
    benefits_found: list[dict],
    profile: UserProfile,
    total_monthly: float,
    language: str,
) -> str:
    """Data-driven eligibility summary — no Gemma call needed, instant response."""
    if not benefits_found:
        if language == "es":
            return (
                "No encontré programas probables con la información proporcionada. "
                "Te recomiendo llamar al **211** para una orientación local — "
                "un especialista puede encontrar ayuda adicional."
            )
        return (
            "I didn't find clear matches based on what you shared. "
            "I'd recommend calling **211** for a local screening — "
            "a specialist may find help I missed."
        )

    top_names = [b["program_name"] for b in benefits_found[:3]]
    extra = len(benefits_found) - 3
    names_str = ", ".join(top_names)
    if extra > 0:
        names_str += f", and {extra} more"

    if language == "es":
        return (
            f"¡Buenas noticias! Encontré **{len(benefits_found)} programa(s)** que pueden aplicar "
            f"para tu hogar: {names_str}. "
            f"El valor estimado combinado es de aproximadamente **${total_monthly:,.0f}/mes**. "
            "Revisa la pestaña **Results** para ver los detalles, documentos necesarios y cómo aplicar. "
            "Recuerda que esto es una estimación — la agencia correspondiente hace la decisión final."
        )
    return (
        f"Great news — I found **{len(benefits_found)} program(s)** that look like a match: "
        f"{names_str}. "
        f"Combined estimated value: **${total_monthly:,.0f}/month**. "
        "Head to the **Results tab** for the full breakdown, required documents, and application links. "
        "This is an estimate — the relevant agency makes the final determination."
    )


async def _extract_profile(messages: list[dict]) -> UserProfile:
    extraction_prompt_template = _load_prompt("extraction_prompt.txt")
    extraction_prompt = extraction_prompt_template.replace("{conversation}", _build_conversation_text(messages))

    # No format constraint (json_mode=False, no response_schema): format constraints
    # trigger Gemma4's thinking mode on Ollama, consuming num_predict tokens before any
    # visible output and forcing a slow retry. Plain JSON instructions in the system
    # prompt work reliably without the overhead.
    extraction_response = await generate(
        messages=[{"role": "user", "content": extraction_prompt}],
        system_prompt=(
            "Extract structured profile data from the conversation. "
            "Return only a valid JSON object. No markdown, no code fences, no explanation."
        ),
        temperature=0.0,
        json_mode=False,
        max_tokens=600,
    )

    profile_data = safe_parse_json(extraction_response, fallback=None)
    if not profile_data or not isinstance(profile_data, dict):
        raise ValueError("Profile extraction did not return a JSON object")
    return UserProfile(**profile_data)


async def _extract_profile_delta(
    latest_user_message: str,
    existing_profile: dict,
    assistant_question: str,
) -> dict:
    """
    Incremental extraction: update the profile from the latest user message only.
    Prompt is ~150 tokens regardless of conversation length, so Gemma4's thinking
    mode is never triggered. Used on turn 2+ when an existing profile is available.
    """
    known = {k: v for k, v in existing_profile.items() if v is not None and k != "profile_complete"}
    known_json = json.dumps(known)

    # Which fields are still missing so Gemma knows what to look for
    missing_fields = [
        f for f in ("state", "household_size", "monthly_income_usd", "children", "has_elderly", "has_disabled")
        if known.get(f) is None
    ]
    missing_hint = f"Still needed for profile_complete: {', '.join(missing_fields)}." if missing_fields else ""

    prompt = (
        f"Known profile so far: {known_json}\n\n"
        f'The assistant just asked: "{assistant_question[:150]}"\n'
        f'User replied: "{latest_user_message}"\n\n'
        f"{missing_hint}\n"
        "Return a JSON object with ONLY the fields to add or update based on the reply. "
        "Set profile_complete=true when state, household_size, monthly_income_usd, children, "
        "has_elderly, and has_disabled are all known (including updates you are returning).\n"
        "Extraction rules:\n"
        "- state: two-letter uppercase US state code\n"
        "- has_elderly: true if anyone 60+, false if user explicitly denies\n"
        "- has_disabled: true if disability present, false if user explicitly denies\n"
        "- has_pregnant: true if pregnancy mentioned\n"
        "- children: exact count of children under 18 (0 if none)\n"
        "- has_children_under_5: true if any child is under 5\n"
        "- has_infant: true if baby/infant mentioned\n"
        "- monthly_income_usd: set to 0 if user says 'no income', 'zero income', or otherwise clearly indicates zero earnings\n"
        "JSON only. No markdown, no explanation."
    )

    response = await generate(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="Output JSON only.",
        temperature=0.0,
        json_mode=False,
        max_tokens=400,
    )

    delta = safe_parse_json(response, fallback={})
    return delta if isinstance(delta, dict) else {}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint:
    1. Turn 1 (no prior profile): Gemma extracts profile from the full (short) first message.
    2. Turn 2+ (prior profile in request): Gemma extracts only from the latest message and
       merges the delta onto the existing profile. Keeps prompt ~150 tokens so Gemma4's
       thinking mode is never triggered by a growing conversation.
    3. If profile is complete, runs eligibility. Otherwise asks the next question.
    """
    language = request.language.value
    messages = [{"role": msg.role, "content": msg.content} for msg in request.history]
    messages.append({"role": "user", "content": request.message})

    existing_profile_dict = request.profile or {}

    try:
        if existing_profile_dict:
            # Find the most recent assistant message so the delta extractor knows context
            assistant_question = next(
                (msg.content for msg in reversed(request.history) if msg.role == "assistant"),
                "",
            )
            delta = await _extract_profile_delta(
                request.message,
                existing_profile_dict,
                assistant_question,
            )
            merged = {**existing_profile_dict, **delta}
            profile = UserProfile(**merged)
        else:
            profile = await _extract_profile(messages)
    except Exception as e:
        logger.warning("Gemma profile extraction unavailable or invalid: %s", e)
        return ChatResponse(
            reply=_model_unavailable_reply(language),
            benefits_found=None,
            next_action="ask_more",
            profile=existing_profile_dict or None,
        )

    # Infer children=0 for single-person households so prefilter works correctly
    if profile.household_size == 1 and profile.children is None:
        profile = profile.model_copy(update={"children": 0})

    profile_dict = profile.model_dump(exclude_none=True)

    needs_more = bool(_missing_profile_fields(profile))
    if needs_more:
        reply = _next_question(profile, language)
        return ChatResponse(reply=reply, benefits_found=None, next_action="ask_more", profile=profile_dict)

    logger.info("Profile complete — running Gemma eligibility before reply")
    eligibility = await run_eligibility_check(profile, language=language)
    benefits_found = [result.model_dump() for result in eligibility.results]

    reply = _build_eligibility_reply(
        benefits_found=benefits_found,
        profile=profile,
        total_monthly=eligibility.total_estimated_monthly_usd,
        language=language,
    )

    return ChatResponse(
        reply=reply,
        benefits_found=benefits_found,
        next_action="show_results" if benefits_found else "ask_more",
        profile=profile_dict,
    )
