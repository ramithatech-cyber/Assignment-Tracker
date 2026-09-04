"""Commit-history signals.

The tarball download (like a shallow clone) carries no history, so these come
from the GitHub commits API.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

GENERIC_MESSAGES = {
    "update", "updates", "updated", "fix", "fixes", "fixed", "change", "changes",
    "changed", "commit", "commits", "final", "final commit", "done", "wip",
    "test", "testing", "asdf", "temp", "stuff", "misc", "new", "edit", "edited",
    "initial commit", "first commit", "add files via upload", "no message",
    ".", "..", "x", "a",
}

CONVENTIONAL = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([^)]+\))?!?:\s+",
    re.IGNORECASE,
)

MERGE = re.compile(r"^(merge|revert)\b", re.IGNORECASE)


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def analyse_commits(commits: list[dict[str, Any]]) -> dict[str, Any]:
    if not commits:
        return {
            "available": False,
            "commit_count": 0,
            "reason": "commit history could not be read from the GitHub API",
        }

    subjects = [(c.get("message") or "").split("\n", 1)[0].strip() for c in commits]
    meaningful = [s for s in subjects if not MERGE.match(s)]

    generic = [s for s in meaningful if s.lower().strip(" .!") in GENERIC_MESSAGES]
    short = [s for s in meaningful if len(s) < 12]
    conventional = [s for s in meaningful if CONVENTIONAL.match(s)]

    dates = [d for d in (_parse_date(c.get("date", "")) for c in commits) if d]
    distinct_days = len({d.date() for d in dates})
    span_days = 0
    if len(dates) >= 2:
        span_days = abs((max(dates) - min(dates)).days)

    denominator = len(meaningful) or 1
    return {
        "available": True,
        # The API caps at 100 per page; more than that is "plenty" either way.
        "commit_count": len(commits),
        "capped": len(commits) >= 100,
        "distinct_days": distinct_days,
        "span_days": span_days,
        "first_commit": min(dates).isoformat() if dates else None,
        "last_commit": max(dates).isoformat() if dates else None,
        "avg_message_length": round(
            sum(len(s) for s in meaningful) / denominator, 1
        ),
        "generic_count": len(generic),
        "generic_ratio": round(len(generic) / denominator, 3),
        "short_message_count": len(short),
        "conventional_ratio": round(len(conventional) / denominator, 3),
        "unique_authors": len({c.get("author", "") for c in commits if c.get("author")}),
        "recent_messages": subjects[:15],
    }
