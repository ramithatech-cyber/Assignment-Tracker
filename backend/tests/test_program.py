"""The 45-day programme: day numbering, date locks, and week rollups."""

from datetime import date, timedelta

import pytest

from app.config import settings
from app.models import ActivityStatus, DailyActivity, utcnow
from app.services import program

ENROLLED = date(2026, 1, 1)


def entry(day: int, hours: float = 2.0, status=ActivityStatus.completed) -> DailyActivity:
    return DailyActivity(
        student_id=1,
        day_number=day,
        activity_date=program.date_for_day(ENROLLED, day),
        status=status,
        notes=f"day {day}",
        hours=hours,
        created_at=utcnow(),
        updated_at=utcnow(),
    )


def test_day_one_is_the_enrolment_date():
    assert program.date_for_day(ENROLLED, 1) == ENROLLED
    assert program.date_for_day(ENROLLED, 45) == ENROLLED + timedelta(days=44)


@pytest.mark.parametrize(
    "today,expected",
    [
        (date(2026, 1, 1), 1),
        (date(2026, 1, 10), 10),
        (date(2025, 12, 30), -1),  # before enrolment
        (date(2026, 2, 20), 51),   # past the end
    ],
)
def test_current_day_number(today, expected):
    assert program.current_day_number(ENROLLED, today) == expected


def test_only_today_is_editable():
    today = date(2026, 1, 10)  # day 10
    days = program.build_days(ENROLLED, [], today)
    editable = [d["day_number"] for d in days if d["editable"]]
    assert editable == [10]


def test_past_days_without_an_entry_are_missed():
    today = date(2026, 1, 5)  # day 5
    days = program.build_days(ENROLLED, [entry(1), entry(2)], today)
    states = {d["day_number"]: d["state"] for d in days}

    assert states[1] == "submitted"
    assert states[2] == "submitted"
    assert states[3] == "missed"      # date passed, nothing filed
    assert states[4] == "missed"
    assert states[5] == "open"        # today, still fillable
    assert states[6] == "upcoming"


def test_the_programme_is_45_days_in_7_weeks():
    days = program.build_days(ENROLLED, [], date(2026, 1, 1))
    assert len(days) == settings.program_days == 45

    weeks = program.build_weeks(days)
    assert len(weeks) == 7
    assert [w["total_days"] for w in weeks] == [7, 7, 7, 7, 7, 7, 3]
    assert sum(w["total_days"] for w in weeks) == 45


def test_week_rollup_counts_only_elapsed_days():
    today = date(2026, 1, 4)  # day 4, mid week 1
    days = program.build_days(ENROLLED, [entry(1), entry(2, hours=3)], today)
    week_one = program.build_weeks(days)[0]

    assert week_one["submitted"] == 2     # days 1 and 2
    assert week_one["missed"] == 1        # day 3
    assert week_one["upcoming"] == 3      # days 5, 6, 7 (day 4 is today, so "open")
    assert week_one["elapsed_days"] == 4  # days 1-4
    assert week_one["hours"] == 5.0
    # Completion is measured against elapsed days, not all 7.
    assert week_one["completion"] == 0.5


def test_summary_counts_and_streak():
    today = date(2026, 1, 6)  # day 6
    entries = [entry(3), entry(4), entry(5)]
    summary = program.summarise(ENROLLED, entries, today)

    assert summary["current_day"] == 6
    assert summary["elapsed_days"] == 6
    assert summary["submitted_days"] == 3
    assert summary["missed_days"] == 3
    assert summary["total_hours"] == 6.0
    # Days 5,4,3 are consecutive up to the last closed day; today isn't filed
    # yet and must not break the streak.
    assert summary["current_streak"] == 3


def test_streak_breaks_on_a_gap():
    today = date(2026, 1, 6)
    summary = program.summarise(ENROLLED, [entry(1), entry(2), entry(5)], today)
    assert summary["current_streak"] == 1  # only day 5


def test_finished_programme():
    today = ENROLLED + timedelta(days=50)
    summary = program.summarise(ENROLLED, [], today)
    assert summary["finished"] is True
    assert summary["elapsed_days"] == 45  # capped at the programme length
