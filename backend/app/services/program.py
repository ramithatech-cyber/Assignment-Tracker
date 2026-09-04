"""The 45-day activity programme: day numbering, date locks, and week rollups.

Days unlock on their own calendar date in the configured programme timezone --
never the server's local time, which would otherwise roll a student's day over
at the wrong hour.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Iterable, Optional

from app.config import settings
from app.models import ActivityStatus, DailyActivity

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9
    ZoneInfo = None  # type: ignore[assignment]

DAYS_PER_WEEK = 7


def program_today() -> date:
    """Today's date in the programme timezone."""
    if ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo(settings.program_timezone)).date()
        except Exception:
            # An invalid IANA name must not take the whole app down.
            pass
    return datetime.utcnow().date()


def date_for_day(enrolled_on: date, day_number: int) -> date:
    return enrolled_on + timedelta(days=day_number - 1)


def current_day_number(enrolled_on: date, today: Optional[date] = None) -> int:
    """1-based day of the programme. May be <1 (not started) or >45 (finished)."""
    return ((today or program_today()) - enrolled_on).days + 1


def day_state(day_number: int, current_day: int, has_entry: bool) -> str:
    """One of: upcoming | open | submitted | missed.

    Only today's day is editable -- yesterday closed when the date rolled over,
    which is the 24-hour lock.
    """
    if day_number > current_day:
        return "upcoming"
    if day_number == current_day:
        return "submitted" if has_entry else "open"
    return "submitted" if has_entry else "missed"


def build_days(
    enrolled_on: date,
    entries: Iterable[DailyActivity],
    today: Optional[date] = None,
) -> list[dict[str, Any]]:
    by_day = {entry.day_number: entry for entry in entries}
    current = current_day_number(enrolled_on, today)

    days: list[dict[str, Any]] = []
    for day_number in range(1, settings.program_days + 1):
        entry = by_day.get(day_number)
        state = day_state(day_number, current, entry is not None)
        days.append(
            {
                "day_number": day_number,
                "date": date_for_day(enrolled_on, day_number).isoformat(),
                "state": state,
                "editable": day_number == current,
                "week": (day_number - 1) // DAYS_PER_WEEK + 1,
                "entry": _entry_payload(entry) if entry else None,
            }
        )
    return days


def _entry_payload(entry: DailyActivity) -> dict[str, Any]:
    return {
        "id": entry.id,
        "status": entry.status.value,
        "notes": entry.notes,
        "hours": entry.hours,
        "link": entry.link,
        "updated_at": entry.updated_at.isoformat(),
    }


def build_weeks(days: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group the day list into weeks. Read-only -- the daily entries are the
    single source of truth, so nothing extra is stored for a week."""
    total_weeks = (settings.program_days + DAYS_PER_WEEK - 1) // DAYS_PER_WEEK
    weeks: list[dict[str, Any]] = []

    for week_number in range(1, total_weeks + 1):
        members = [d for d in days if d["week"] == week_number]
        if not members:
            continue

        submitted = [d for d in members if d["state"] == "submitted"]
        missed = [d for d in members if d["state"] == "missed"]
        upcoming = [d for d in members if d["state"] == "upcoming"]
        elapsed = len(members) - len(upcoming)

        hours = sum((d["entry"] or {}).get("hours", 0.0) for d in submitted)
        statuses = [(d["entry"] or {}).get("status") for d in submitted]

        weeks.append(
            {
                "week_number": week_number,
                "start_date": members[0]["date"],
                "end_date": members[-1]["date"],
                "day_numbers": [d["day_number"] for d in members],
                "total_days": len(members),
                "elapsed_days": elapsed,
                "submitted": len(submitted),
                "missed": len(missed),
                "upcoming": len(upcoming),
                "completion": round(len(submitted) / elapsed, 3) if elapsed else 0.0,
                "hours": round(hours, 2),
                "fully_completed": sum(
                    1 for s in statuses if s == ActivityStatus.completed.value
                ),
                "partial": sum(1 for s in statuses if s == ActivityStatus.partial.value),
                "skipped": sum(1 for s in statuses if s == ActivityStatus.skipped.value),
                "state": (
                    "upcoming"
                    if elapsed == 0
                    else "in_progress"
                    if upcoming
                    else "complete"
                ),
            }
        )
    return weeks


def summarise(
    enrolled_on: date,
    entries: list[DailyActivity],
    today: Optional[date] = None,
) -> dict[str, Any]:
    """Headline numbers for a student's programme progress."""
    current = current_day_number(enrolled_on, today)
    total = settings.program_days
    elapsed = max(0, min(current, total))
    submitted = len(entries)

    by_day = {e.day_number for e in entries}
    streak = 0
    # Count back from the most recent elapsed day. Today not being filled in yet
    # shouldn't break a streak, so start at the last closed day.
    cursor = current - 1 if current not in by_day else current
    while cursor >= 1 and cursor in by_day:
        streak += 1
        cursor -= 1

    return {
        "enrolled_on": enrolled_on.isoformat(),
        "total_days": total,
        "current_day": current,
        "elapsed_days": elapsed,
        "submitted_days": submitted,
        "missed_days": max(0, elapsed - submitted),
        "completion": round(submitted / elapsed, 3) if elapsed else 0.0,
        "total_hours": round(sum(e.hours for e in entries), 2),
        "current_streak": streak,
        "started": current >= 1,
        "finished": current > total,
    }
