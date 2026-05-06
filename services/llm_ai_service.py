from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from config import (
    OLLAMA_DEEPSEEK_MODEL,
    OLLAMA_OPENAI_API_KEY,
    OLLAMA_OPENAI_BASE_URL,
    OLLAMA_TIMEOUT_SECONDS,
)
from utils.ai_result_parser import (
    normalize_feedback_result,
    normalize_next_action_result,
    normalize_precheck_result,
    parse_ai_json_or_fallback,
)
from utils.exceptions import (
    AIConnectionError,
    AIModelNotFoundError,
    AIResponseFormatError,
    AIServiceError,
    AITimeoutError,
)


class LLMAIService:
    def __init__(self, timeout_sec: int = OLLAMA_TIMEOUT_SECONDS, client: OpenAI | None = None) -> None:
        self.timeout_sec = timeout_sec
        self.client = client or OpenAI(
            base_url=OLLAMA_OPENAI_BASE_URL,
            api_key=OLLAMA_OPENAI_API_KEY,
            timeout=timeout_sec,
        )
        self.model = OLLAMA_DEEPSEEK_MODEL

    def analyze_application(self, application_data: dict) -> dict:
        system_prompt = (
            "You are a strict study-abroad precheck assistant. "
            "Return ONLY valid JSON object with keys: "
            "conclusion, risk_level, issues, suggestions, summary. "
            "risk_level must be LOW, MEDIUM, or HIGH. "
            "issues and suggestions must be arrays of concise strings."
        )
        payload = {
            "task": "AI precheck before submission",
            "application_data": application_data,
            "constraints": "advice only, do not make final approval decisions",
        }
        result = self._chat_json(system_prompt, payload)
        return normalize_precheck_result(result)

    def summarize_feedback(self, feedback_text: str, application_data: dict | None = None) -> dict:
        system_prompt = (
            "You are an assistant explaining school feedback for a study-abroad workflow. "
            "Return ONLY valid JSON object with keys: "
            "feedback_type, core_reasons, recommended_actions, suggest_change_major, "
            "suggest_transfer_university, summary. "
            "core_reasons and recommended_actions must be arrays of strings. "
            "The two suggest_* fields must be booleans."
        )
        payload = {
            "task": "Interpret school feedback",
            "feedback_text": feedback_text,
            "application_data": application_data or {},
            "constraints": "advice only; respect existing business state machine",
        }
        result = self._chat_json(system_prompt, payload)
        return normalize_feedback_result(result)

    def suggest_next_action(self, application_data: dict, role_code: str, quota_info: dict | None = None) -> dict:
        system_prompt = (
            "You are an assistant for next-step action recommendations in a study-abroad system. "
            "Return ONLY valid JSON object with keys: "
            "operation_explanations, recommended_next_action, reasoning, alternatives, summary. "
            "operation_explanations, reasoning, alternatives must be arrays of strings."
        )
        payload = {
            "task": "Suggest next action under current workflow constraints",
            "application_data": application_data,
            "role_code": role_code,
            "quota_info": quota_info or {},
            "constraints": (
                "advice only; no override of permission checks, status checks, "
                "quota checks, or database operations"
            ),
        }
        result = self._chat_json(system_prompt, payload)
        return normalize_next_action_result(result)

    def _chat_json(self, system_prompt: str, payload: dict[str, Any]) -> dict:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
            )
        except Exception as exc:
            raise self._map_exception(exc) from exc

        content = ""
        if response.choices and response.choices[0].message:
            content = response.choices[0].message.content or ""

        parsed = parse_ai_json_or_fallback(content)
        if parsed.get("parse_mode") == "fallback_text" and not parsed.get("summary"):
            raise AIResponseFormatError("AI response is empty or unparsable.")
        return parsed

    def _map_exception(self, exc: Exception) -> AIServiceError:
        text = str(exc).lower()
        if "timed out" in text or "timeout" in text:
            return AITimeoutError("AI request timed out.")
        if "connection" in text or "refused" in text or "localhost:11434" in text:
            return AIConnectionError("Cannot connect to Ollama. Please start local Ollama service.")
        if "model" in text and ("not found" in text or "pull" in text):
            return AIModelNotFoundError(
                "Model deepseek-r1:8b not found. Run: ollama pull deepseek-r1:8b"
            )
        return AIServiceError(f"Local AI call failed: {exc}")
