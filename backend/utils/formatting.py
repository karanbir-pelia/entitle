"""
Response formatting helpers for Entitle backend.
"""

import re
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def format_currency(amount: float) -> str:
    """Format a dollar amount with commas and no decimal if whole number."""
    if amount == int(amount):
        return f"${int(amount):,}"
    return f"${amount:,.2f}"


def strip_markdown_fences(text: str) -> str:
    """
    Strip markdown code fences from LLM responses before JSON parsing.
    Gemma 4 sometimes wraps JSON in ```json ... ``` blocks.
    """
    # Remove ```json\n...\n``` or ```\n...\n```
    text = text.strip()
    pattern = r"^```(?:json)?\s*\n?(.*?)\n?```$"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def safe_parse_json(text: str, fallback: dict | list | None = None) -> dict | list | None:
    """
    Safely parse JSON from an LLM response.
    Strips markdown fences before parsing and attempts json-repair for
    malformed-but-recoverable model output.
    Returns fallback on failure.
    """
    if not text or not text.strip():
        logger.error("JSON parse failed: empty response")
        return fallback

    cleaned = strip_markdown_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning("Strict JSON parse failed, trying repair: %s | Raw text (first 300 chars): %s", e, text[:300])

    try:
        from json_repair import repair_json

        repaired: Any = repair_json(cleaned, return_objects=True)
        if isinstance(repaired, (dict, list)):
            return repaired

        return json.loads(repaired)
    except Exception as e:
        logger.error("JSON repair failed: %s | Raw text (first 300 chars): %s", e, text[:300])
        return fallback


def truncate(text: str, max_chars: int = 500) -> str:
    """Truncate text to a maximum character count."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "…"
