"""
All Gemma 4 inference logic.
Supports two backends:
  1. Ollama (local, offline) — primary
  2. Gemini API (hosted) — fallback for demo/Kaggle

Never call the backends directly from routers.
Always use generate() or generate_with_image().
"""

import logging
import httpx
from typing import Any, List, Optional
from config import settings

logger = logging.getLogger(__name__)


def _http_timeout() -> httpx.Timeout:
    return httpx.Timeout(settings.model_timeout_seconds, connect=10.0)


def _schema_instruction(response_schema: dict[str, Any] | None) -> str:
    if not response_schema:
        return ""

    import json

    return (
        "\n\nReturn JSON that conforms to this JSON Schema. "
        "Do not include markdown or explanatory text.\n"
        f"{json.dumps(response_schema)}"
    )


def _message_content(data: dict[str, Any]) -> str:
    message = data.get("message") or {}
    return message.get("content") or ""


def _done_reason(data: dict[str, Any]) -> str:
    return str(data.get("done_reason") or data.get("done") or "unknown")


# ── Ollama Backend ─────────────────────────────────────────────────────────────

async def call_ollama(
    messages: List[dict],
    system_prompt: str = "",
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
    json_mode: bool = False,
    response_schema: Optional[dict[str, Any]] = None,
) -> str:
    """
    Call Gemma 4 via Ollama REST API.

    Format constraints (json_mode / response_schema) trigger Gemma4's internal
    thinking mode on Ollama, which consumes num_predict tokens before any visible
    output appears. When that happens we do a SINGLE retry using plain JSON
    instructions in the system message — no intermediate json-mode step.
    """
    if max_tokens is None:
        max_tokens = settings.max_tokens

    payload: dict = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": False,
        # Disable Gemma 4's hidden thinking tokens. Without this, gemma4:e4b
        # frequently consumes the entire num_predict budget on internal reasoning
        # and emits zero visible characters (done_reason=length, length=0).
        "think": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }

    if system_prompt:
        payload["system"] = system_prompt

    if response_schema:
        payload["format"] = response_schema
    elif json_mode:
        payload["format"] = "json"

    logger.info(
        "Calling Ollama model=%s, messages=%d, max_tokens=%d, timeout=%.0fs",
        settings.ollama_model,
        len(messages),
        max_tokens,
        settings.model_timeout_seconds,
    )

    async with httpx.AsyncClient(timeout=_http_timeout()) as client:
        try:
            response = await client.post(
                f"{settings.ollama_base_url}/api/chat",
                json=payload,
            )
        except httpx.TimeoutException:
            logger.warning(
                "Ollama request timed out after %.0fs for model=%s",
                settings.model_timeout_seconds,
                settings.ollama_model,
            )
            raise
        response.raise_for_status()
        data = response.json()
        content = _message_content(data)
        done = _done_reason(data)
        logger.info(
            "Ollama response received, length=%d chars, done_reason=%s",
            len(content),
            done,
        )

        # Single retry: format constraints caused thinking-token overflow.
        # Go straight to plain JSON instructions — skip the json-mode middle step,
        # which also fails when the prompt is complex enough to trigger thinking.
        if (response_schema or json_mode) and not content.strip():
            logger.warning(
                "Ollama format mode returned empty (done_reason=%s); "
                "retrying with plain JSON instructions",
                done,
            )
            plain_system = (
                (system_prompt or "")
                + _schema_instruction(response_schema)
                + "\n\nReturn only a valid JSON object. No prose. No markdown."
            )
            plain_payload = dict(payload)
            plain_payload.pop("format", None)
            plain_payload.pop("system", None)
            plain_payload["messages"] = [
                {"role": "system", "content": plain_system},
                *messages,
            ]
            try:
                plain_response = await client.post(
                    f"{settings.ollama_base_url}/api/chat",
                    json=plain_payload,
                )
            except httpx.TimeoutException:
                logger.warning(
                    "Ollama plain JSON retry timed out after %.0fs for model=%s",
                    settings.model_timeout_seconds,
                    settings.ollama_model,
                )
                raise
            plain_response.raise_for_status()
            plain_data = plain_response.json()
            content = _message_content(plain_data)
            logger.info(
                "Ollama plain JSON retry: length=%d chars, done_reason=%s",
                len(content),
                _done_reason(plain_data),
            )

        return content


# ── Gemini API Backend ─────────────────────────────────────────────────────────

async def call_gemini_api(
    messages: List[dict],
    system_prompt: str = "",
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
    json_mode: bool = False,
    response_schema: Optional[dict[str, Any]] = None,
) -> str:
    """
    Call Gemma 4 via Google's Gemini API.
    Uses google-genai SDK.
    Model: gemma-4-26b-a4b-it or gemma-4-31b-it
    """
    from google import genai
    from google.genai import types

    if max_tokens is None:
        max_tokens = settings.max_tokens

    client = genai.Client(api_key=settings.gemini_api_key)

    # Convert messages from OpenAI-style to Gemini format
    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part(text=msg["content"])],
            )
        )

    config = types.GenerateContentConfig(
        system_instruction=system_prompt if system_prompt else None,
        temperature=temperature,
        max_output_tokens=max_tokens,
        response_mime_type="application/json" if json_mode else "text/plain",
        response_schema=response_schema if response_schema else None,
    )

    # Add thinking budget if enabled (Gemma 4 configurable thinking)
    if settings.enable_thinking:
        config.thinking_config = types.ThinkingConfig(
            thinking_budget=1024  # tokens for thinking — more for complex eligibility
        )

    logger.info("Calling Gemini API model=%s, messages=%d", settings.gemini_model, len(messages))

    response = await client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=contents,
        config=config,
    )
    content: str = response.text
    logger.info("Gemini API response received, length=%d chars", len(content))
    return content


# ── Unified Interface ──────────────────────────────────────────────────────────

async def generate(
    messages: List[dict],
    system_prompt: str = "",
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
    json_mode: bool = False,
    response_schema: Optional[dict[str, Any]] = None,
) -> str:
    """
    Route to the configured backend.
    Use this function everywhere else in the codebase.
    Never call call_ollama or call_gemini_api directly.
    """
    if settings.model_backend == "ollama":
        return await call_ollama(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
            response_schema=response_schema,
        )
    else:
        return await call_gemini_api(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
            response_schema=response_schema,
        )


# ── Vision / Multimodal ────────────────────────────────────────────────────────

async def generate_with_image(
    text_prompt: str,
    image_base64: str,
    image_mime_type: str = "image/jpeg",
    system_prompt: str = "",
) -> str:
    """
    Call Gemma 4 with an image input (for document reading).
    Ollama: uses /api/chat with images field.
    Gemini API: uses inline_data blob.
    """
    if settings.model_backend == "ollama":
        payload: dict = {
            "model": settings.ollama_model,
            "messages": [
                {
                    "role": "user",
                    "content": text_prompt,
                    "images": [image_base64],
                }
            ],
            "stream": False,
            "think": False,
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=_http_timeout()) as client:
            try:
                response = await client.post(
                    f"{settings.ollama_base_url}/api/chat",
                    json=payload,
                )
            except httpx.TimeoutException:
                logger.warning(
                    "Ollama vision request timed out after %.0fs for model=%s",
                    settings.model_timeout_seconds,
                    settings.ollama_model,
                )
                raise
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]

    else:
        # Gemini API vision
        from google import genai
        from google.genai import types
        import base64

        client = genai.Client(api_key=settings.gemini_api_key)

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        inline_data=types.Blob(
                            mime_type=image_mime_type,
                            data=base64.b64decode(image_base64),
                        )
                    ),
                    types.Part(text=text_prompt),
                ],
            )
        ]

        config = types.GenerateContentConfig(
            system_instruction=system_prompt if system_prompt else None,
            temperature=0.2,
            max_output_tokens=1024,
        )

        response = await client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=contents,
            config=config,
        )
        return response.text
