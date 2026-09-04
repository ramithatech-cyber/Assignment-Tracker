"""The OpenAI call.

Uses structured outputs (a strict JSON schema) so the response shape is
guaranteed by the API -- there is no parsing, no regex, and no "the model
returned prose today" failure mode.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

from app.config import settings
from app.services.errors import AnalysisError
from app.services.scoring import RUBRIC, rubric_prompt_block

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "reviewer.md"

_CATEGORY_KEYS = [item["key"] for item in RUBRIC]

REVIEW_SCHEMA: dict[str, Any] = {
    "name": "repository_review",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["summary", "categories", "strengths", "improvements"],
        "properties": {
            "summary": {"type": "string"},
            "categories": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["key", "score", "justification"],
                    "properties": {
                        "key": {"type": "string", "enum": _CATEGORY_KEYS},
                        "score": {"type": "number"},
                        "justification": {"type": "string"},
                    },
                },
            },
            "strengths": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["title", "detail", "file"],
                    "properties": {
                        "title": {"type": "string"},
                        "detail": {"type": "string"},
                        "file": {"type": ["string", "null"]},
                    },
                },
            },
            "improvements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["title", "detail", "suggestion", "severity", "file"],
                    "properties": {
                        "title": {"type": "string"},
                        "detail": {"type": "string"},
                        "suggestion": {"type": "string"},
                        "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                        "file": {"type": ["string", "null"]},
                    },
                },
            },
        },
    },
}


def _system_prompt() -> str:
    try:
        base = PROMPT_PATH.read_text(encoding="utf-8")
    except OSError:
        base = "You are a senior engineer reviewing a student's repository."
    return f"{base}\n\n## Rubric\n\n{rubric_prompt_block()}\n"


def _client() -> OpenAI:
    if not settings.openai_api_key:
        raise AnalysisError(
            "The server has no OPENAI_API_KEY configured, so submissions cannot "
            "be analysed. Ask your administrator to set it.",
            status_code=503,
        )
    return OpenAI(api_key=settings.openai_api_key, timeout=settings.openai_timeout)


def review_repository(
    bundle: str,
    assignment_title: str,
    assignment_requirements: str,
) -> tuple[dict[str, Any], int]:
    """Returns (parsed review, tokens used)."""
    import json

    brief = assignment_requirements.strip() or (
        "No explicit requirements were provided. Judge correctness and "
        "completeness against what the repository itself claims to do."
    )

    user_content = (
        f"# Assignment\n\n**Title:** {assignment_title}\n\n"
        f"**Requirements the student had to meet:**\n\n{brief}\n\n"
        f"---\n\n{bundle}"
    )

    client = _client()
    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": _system_prompt()},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_schema", "json_schema": REVIEW_SCHEMA},
        )
    except APITimeoutError as exc:
        raise AnalysisError(
            "The AI review timed out. This usually means the repository is very "
            "large — try again, or submit a smaller repository.",
            status_code=504,
        ) from exc
    except RateLimitError as exc:
        raise AnalysisError(
            "The OpenAI rate limit or quota was reached. Try again shortly.",
            status_code=429,
        ) from exc
    except APIConnectionError as exc:
        raise AnalysisError("Could not reach OpenAI.", status_code=502) from exc
    except APIStatusError as exc:
        detail = "invalid API key" if exc.status_code == 401 else f"HTTP {exc.status_code}"
        raise AnalysisError(f"OpenAI rejected the request ({detail}).", status_code=502) from exc

    choice = response.choices[0]
    if getattr(choice.message, "refusal", None):
        raise AnalysisError("The model declined to review this repository.", status_code=422)

    content = choice.message.content or "{}"
    try:
        review = json.loads(content)
    except json.JSONDecodeError as exc:
        raise AnalysisError("The AI response could not be parsed.", status_code=502) from exc

    tokens = response.usage.total_tokens if response.usage else 0
    return review, tokens
