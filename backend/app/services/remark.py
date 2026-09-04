"""Generates an admin-facing overall remark across a student's whole body of work.

This reads the reports that were already produced for each submission rather
than re-analysing any repository, so it is one cheap call regardless of how many
submissions the student has.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

from app.config import settings
from app.services.errors import AnalysisError

SYSTEM_PROMPT = """You are a senior engineer writing an end-of-review verdict on a
student for their course administrator. You are given every assignment they have
submitted, the scores and findings those submissions produced, and their daily
activity log.

Rules:

1. **Judge the pattern, not one submission.** The admin can already read each
   individual report. Your value is what recurs across all of them: the habits
   that keep costing marks, and the ones that keep earning them.
2. **Use the numbers you are given.** Never invent a score, a count, or a trend.
   If there is only one submission, say the evidence is thin rather than
   describing a trajectory.
3. **Separate ability from consistency.** A student who scores well but files
   almost no daily activity has a different problem from one who shows up every
   day but scores poorly. Say which one this is.
4. **Be specific and usable.** "Needs to improve code quality" is worthless.
   "Every submission has lost marks on Testing - they have never shipped a test
   file" is actionable.
5. Write about the student in the third person, for a colleague. Direct and
   fair, neither harsh nor padded. No greetings or sign-offs.

`trajectory` must be `insufficient_data` when there are fewer than two graded
submissions."""

REMARK_SCHEMA: dict[str, Any] = {
    "name": "student_remark",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["summary", "trajectory", "strengths", "concerns", "recommendation"],
        "properties": {
            "summary": {
                "type": "string",
                "description": "3-5 sentences: overall verdict on this student's work.",
            },
            "trajectory": {
                "type": "string",
                "enum": ["improving", "steady", "declining", "insufficient_data"],
            },
            "strengths": {
                "type": "array",
                "description": "2-4 patterns that recur across their submissions.",
                "items": {"type": "string"},
            },
            "concerns": {
                "type": "array",
                "description": "2-4 recurring problems, most important first.",
                "items": {"type": "string"},
            },
            "recommendation": {
                "type": "string",
                "description": "The single most valuable thing this student should do next.",
            },
        },
    },
}


def build_context(
    student_name: str,
    performance: dict[str, Any],
    submissions: list[dict[str, Any]],
) -> str:
    """Flatten everything known about a student into one prompt."""
    programme = performance["programme"]

    lines = [
        f"# Student: {student_name}",
        "",
        "## Overall figures",
        f"- Submissions: {performance['submission_count']} "
        f"({performance['failed_count']} failed to analyse)",
        f"- Average score: {performance['average_score'] if performance['average_score'] is not None else 'no graded submissions'}",
        f"- Best score: {performance['best_score'] if performance['best_score'] is not None else 'n/a'}",
        f"- Performance level: {performance['performance_level']} "
        f"(index {performance['performance_index']})",
        "",
        "## Daily activity programme",
        f"- Day {programme['current_day']} of {programme['total_days']}",
        f"- Submitted {programme['submitted_days']} of {programme['elapsed_days']} elapsed days "
        f"({round(programme['completion'] * 100)}% consistency)",
        f"- Missed days: {programme['missed_days']}",
        f"- Current streak: {programme['current_streak']} days",
        f"- Total hours logged: {programme['total_hours']}",
        "",
        "## Submissions, oldest first",
    ]

    graded = [s for s in submissions if s.get("total_score") is not None]
    if not graded:
        lines.append("(none analysed successfully yet)")

    # Oldest first so any trend reads in the natural direction.
    for entry in reversed(submissions):
        title = entry.get("assignment_title") or f"Assignment {entry.get('assignment_id')}"
        if entry.get("total_score") is None:
            lines.append(
                f"\n### {title} — FAILED: {entry.get('error_message') or 'unknown error'}"
            )
            continue

        lines.append(
            f"\n### {title} — {entry['total_score']}/100 (grade {entry.get('grade')})"
            f"  ·  {entry.get('repo_url')}  ·  {entry.get('created_at')}"
        )

        report = entry.get("report") or {}
        categories = report.get("category_scores") or []
        if categories:
            scores = ", ".join(
                f"{c['label']} {c['score']}/{c['max_score']}" for c in categories
            )
            lines.append(f"- Category scores: {scores}")
        if report.get("summary"):
            lines.append(f"- Reviewer summary: {report['summary']}")
        for item in (report.get("strengths") or [])[:3]:
            lines.append(f"- Strength: {item.get('title')}")
        for item in (report.get("improvements") or [])[:4]:
            lines.append(
                f"- Improvement ({item.get('severity')}): {item.get('title')}"
            )
        for cap in (report.get("applied_caps") or [])[:4]:
            lines.append(f"- Automatic limit: {cap}")

    return "\n".join(lines)


def generate(context: str) -> tuple[dict[str, Any], int]:
    """Returns (remark, tokens used)."""
    if not settings.openai_api_key:
        raise AnalysisError(
            "The server has no OPENAI_API_KEY configured, so remarks cannot be "
            "generated.",
            status_code=503,
        )

    client = OpenAI(api_key=settings.openai_api_key, timeout=settings.openai_timeout)
    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.3,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": context},
            ],
            response_format={"type": "json_schema", "json_schema": REMARK_SCHEMA},
        )
    except APITimeoutError as exc:
        raise AnalysisError("Generating the remark timed out.", status_code=504) from exc
    except RateLimitError as exc:
        raise AnalysisError(
            "The OpenAI rate limit or quota was reached. Try again shortly.",
            status_code=429,
        ) from exc
    except APIConnectionError as exc:
        raise AnalysisError("Could not reach OpenAI.", status_code=502) from exc
    except APIStatusError as exc:
        detail = "invalid API key" if exc.status_code == 401 else f"HTTP {exc.status_code}"
        raise AnalysisError(
            f"OpenAI rejected the request ({detail}).", status_code=502
        ) from exc

    choice = response.choices[0]
    if getattr(choice.message, "refusal", None):
        raise AnalysisError("The model declined to write this remark.", status_code=422)

    try:
        remark = json.loads(choice.message.content or "{}")
    except json.JSONDecodeError as exc:
        raise AnalysisError("The AI response could not be parsed.", status_code=502) from exc

    return remark, (response.usage.total_tokens if response.usage else 0)


def is_stale(remark: Any, submission_count: int, submitted_days: int) -> Optional[str]:
    """Why a cached remark no longer reflects the student, if it doesn't."""
    if remark is None:
        return None
    new_submissions = submission_count - remark.based_on_submissions
    new_days = submitted_days - remark.based_on_days

    parts = []
    if new_submissions > 0:
        parts.append(f"{new_submissions} new submission{'s' if new_submissions > 1 else ''}")
    if new_days > 0:
        parts.append(f"{new_days} new daily entr{'ies' if new_days > 1 else 'y'}")
    return " and ".join(parts) if parts else None
