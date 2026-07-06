from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
from jsonschema import Draft202012Validator
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from .models import LLMConfig


class LLMResponseError(RuntimeError):
    pass


def load_json_schema(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    with path.open("r", encoding="utf-8") as handle:
        schema = json.load(handle)
    if not isinstance(schema, dict):
        raise ValueError("Output schema must be a JSON object.")
    Draft202012Validator.check_schema(schema)
    return schema


def call_llama_cpp(
    prompt: str,
    llm_config: LLMConfig,
    *,
    retries: int,
    timeout_seconds: float,
    output_schema: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | list[Any], str]:
    attempts = max(1, retries + 1)

    @retry(
        retry=retry_if_exception_type(LLMResponseError),
        stop=stop_after_attempt(attempts),
        wait=wait_fixed(0.5),
        reraise=True,
    )
    def _call() -> tuple[dict[str, Any] | list[Any], str]:
        payload = {
            "model": llm_config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": llm_config.temperature,
            "max_tokens": llm_config.max_tokens,
        }
        response = httpx.post(llm_config.base_url, json=payload, timeout=timeout_seconds)
        response.raise_for_status()
        data = response.json()
        raw_text = _extract_chat_content(data)
        parsed = _parse_json_text(raw_text)
        if output_schema is not None:
            Draft202012Validator(output_schema).validate(parsed)
        return parsed, raw_text

    return _call()


def _extract_chat_content(response_json: dict[str, Any]) -> str:
    try:
        content = response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMResponseError("LLM response was not OpenAI chat-completions compatible.") from exc
    if not isinstance(content, str) or not content.strip():
        raise LLMResponseError("LLM response content was empty.")
    return content.strip()


def _parse_json_text(text: str) -> dict[str, Any] | list[Any]:
    cleaned = _strip_markdown_fence(text)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LLMResponseError("LLM response content was not valid JSON.") from exc
    if not isinstance(parsed, (dict, list)):
        raise LLMResponseError("LLM response JSON must be an object or array.")
    return parsed


def _strip_markdown_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) >= 3 and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return stripped

