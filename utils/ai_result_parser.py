from __future__ import annotations

import json
import re


def parse_ai_json_or_fallback(raw_text: str) -> dict:
    text = (raw_text or "").strip()
    if not text:
        return {"raw_text": "", "parse_mode": "empty"}

    parsed = _try_parse_json(text)
    if parsed is not None:
        parsed["parse_mode"] = "json"
        parsed["raw_text"] = text
        return parsed

    block = _extract_json_block(text)
    if block:
        parsed = _try_parse_json(block)
        if parsed is not None:
            parsed["parse_mode"] = "json_block"
            parsed["raw_text"] = text
            return parsed

    return {"raw_text": text, "parse_mode": "fallback_text", "summary": _compact_text(text)}


def normalize_precheck_result(data: dict) -> dict:
    return {
        "conclusion": _str(data.get("conclusion"), "Needs manual confirmation."),
        "risk_level": _normalize_risk_level(data.get("risk_level")),
        "issues": _to_list(data.get("issues")),
        "suggestions": _to_list(data.get("suggestions")),
        "summary": _str(data.get("summary"), ""),
        "parse_mode": _str(data.get("parse_mode"), "fallback_text"),
        "raw_text": _str(data.get("raw_text"), ""),
    }


def normalize_feedback_result(data: dict) -> dict:
    return {
        "feedback_type": _str(data.get("feedback_type"), "UNKNOWN"),
        "core_reasons": _to_list(data.get("core_reasons")),
        "recommended_actions": _to_list(data.get("recommended_actions")),
        "suggest_change_major": _to_bool(data.get("suggest_change_major")),
        "suggest_transfer_university": _to_bool(data.get("suggest_transfer_university")),
        "summary": _str(data.get("summary"), ""),
        "parse_mode": _str(data.get("parse_mode"), "fallback_text"),
        "raw_text": _str(data.get("raw_text"), ""),
    }


def normalize_next_action_result(data: dict) -> dict:
    return {
        "operation_explanations": _to_list(data.get("operation_explanations")),
        "recommended_next_action": _str(data.get("recommended_next_action"), "MANUAL_REVIEW"),
        "reasoning": _to_list(data.get("reasoning")),
        "alternatives": _to_list(data.get("alternatives")),
        "summary": _str(data.get("summary"), ""),
        "parse_mode": _str(data.get("parse_mode"), "fallback_text"),
        "raw_text": _str(data.get("raw_text"), ""),
    }


def _extract_json_block(text: str) -> str | None:
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _try_parse_json(text: str) -> dict | None:
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _compact_text(text: str, limit: int = 500) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[:limit] + "..."


def _normalize_risk_level(value: object) -> str:
    text = _str(value, "MEDIUM").upper()
    if text in {"LOW", "MEDIUM", "HIGH"}:
        return text
    if text in {"L", "LOW_RISK"}:
        return "LOW"
    if text in {"M", "MID", "MED"}:
        return "MEDIUM"
    if text in {"H", "HIGH_RISK"}:
        return "HIGH"
    return "MEDIUM"


def _to_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = [p.strip() for p in re.split(r"[;\n]", value) if p.strip()]
        return parts
    return []


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _str(value: object, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default
