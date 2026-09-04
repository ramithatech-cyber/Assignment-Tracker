"""Turns a student's raw activity into a performance level for the admin view.

Two independent signals are blended: how well their submitted repositories
score, and how consistently they file their daily activity. A student with no
graded submissions is judged on consistency alone rather than being scored 0.
"""

from __future__ import annotations

from typing import Any, Optional

LEVELS = [
    (85, "Excellent", "emerald"),
    (70, "Strong", "lime"),
    (55, "On track", "amber"),
    (40, "Needs support", "orange"),
    (0, "At risk", "red"),
]

# Weighting when both signals are present.
SCORE_WEIGHT = 0.6
CONSISTENCY_WEIGHT = 0.4


def level_for(index: Optional[float]) -> tuple[str, str]:
    if index is None:
        return "No data", "stone"
    for threshold, label, tone in LEVELS:
        if index >= threshold:
            return label, tone
    return "At risk", "red"


def performance_index(
    average_score: Optional[float],
    completion: Optional[float],
) -> Optional[float]:
    """0-100. None when there is nothing at all to judge."""
    consistency = None if completion is None else completion * 100

    if average_score is None and consistency is None:
        return None
    if average_score is None:
        return round(consistency, 1)
    if consistency is None:
        return round(average_score, 1)

    return round(average_score * SCORE_WEIGHT + consistency * CONSISTENCY_WEIGHT, 1)


def build_row(
    student: Any,
    scores: list[float],
    submission_count: int,
    failed_count: int,
    programme: dict[str, Any],
    last_active: Optional[str],
) -> dict[str, Any]:
    average = round(sum(scores) / len(scores), 1) if scores else None
    best = max(scores) if scores else None

    # Only judge consistency once the programme has actually started.
    completion = programme["completion"] if programme["elapsed_days"] > 0 else None
    index = performance_index(average, completion)
    label, tone = level_for(index)

    return {
        "student_id": student.id,
        "student_name": student.full_name,
        "email": student.email,
        "joined_at": student.created_at.isoformat(),
        "submission_count": submission_count,
        "failed_count": failed_count,
        "average_score": average,
        "best_score": best,
        "programme": programme,
        "performance_index": index,
        "performance_level": label,
        "performance_tone": tone,
        "last_active": last_active,
    }
