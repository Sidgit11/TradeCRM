"""Shared utilities for parsing Gemini AI model outputs."""
import json
import re
from typing import Dict, Any, Optional

from app.logging_config import get_logger

logger = get_logger("utils.gemini")

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"


def safe_parse_json(text: str, fallback: Optional[Dict[str, Any]] = None) -> dict:
    """Robustly parse JSON from Gemini, handling newlines inside strings.

    Gemini 2.5 often puts actual newlines inside JSON string values
    (e.g. "body": "Dear Hans,\\nThank you...") which breaks json.loads().
    This function walks the text character by character and escapes
    newlines that appear inside quoted strings.
    """
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Walk through text and escape newlines inside string values
    result = []
    in_string = False
    escape_next = False
    for ch in text:
        if escape_next:
            result.append(ch)
            escape_next = False
            continue
        if ch == '\\':
            result.append(ch)
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if in_string and ch == '\n':
            result.append('\\n')
            continue
        if in_string and ch == '\r':
            result.append('\\r')
            continue
        result.append(ch)

    fixed = ''.join(result)
    try:
        parsed = json.loads(fixed)
        logger.debug("JSON parsed successfully after newline fix")
        return parsed
    except json.JSONDecodeError as e:
        logger.error("JSON parse failed even after newline fix: %s | text_start: %s", str(e), repr(fixed[:200]))
        if fallback is not None:
            return fallback
        return {}


def extract_gemini_text(parts: list) -> str:
    """Extract the non-thinking text part from Gemini response parts.

    Gemini 2.5 returns multiple parts — some with thought: true (thinking content).
    This finds the first non-thinking text part.
    """
    for part in parts:
        if part.get("thought"):
            continue
        if "text" in part:
            return part["text"]
    # Fallback: return first text part even if it's thinking
    for part in parts:
        if "text" in part:
            return part["text"]
    return ""
