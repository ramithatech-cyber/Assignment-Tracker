"""The student-facing 45-day activity programme."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.auth import get_current_user
from app.config import settings
from app.database import get_session
from app.models import ActivityStatus, DailyActivity, Role, User, utcnow
from app.schemas import ActivityUpsert, DaysResponse, WeeksResponse
from app.services import program

router = APIRouter(prefix="/api/activities", tags=["activities"])


def _ensure_enrolled(user: User, session: Session) -> date:
    """Every student needs a day 1. Backfill from their registration date."""
    if user.enrolled_on is None:
        user.enrolled_on = user.created_at.date()
        session.add(user)
        session.commit()
        session.refresh(user)
    return user.enrolled_on


def _entries_for(student_id: int, session: Session) -> list[DailyActivity]:
    return list(
        session.exec(
            select(DailyActivity)
            .where(DailyActivity.student_id == student_id)
            .order_by(DailyActivity.day_number)
        ).all()
    )


@router.get("/days", response_model=DaysResponse)
def list_days(
    user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> DaysResponse:
    if user.role != Role.student:
        raise HTTPException(403, "The activity programme is for students.")

    enrolled_on = _ensure_enrolled(user, session)
    entries = _entries_for(user.id, session)
    days = program.build_days(enrolled_on, entries)

    return DaysResponse(days=days, summary=program.summarise(enrolled_on, entries))


@router.get("/weeks", response_model=WeeksResponse)
def list_weeks(
    user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> WeeksResponse:
    if user.role != Role.student:
        raise HTTPException(403, "The activity programme is for students.")

    enrolled_on = _ensure_enrolled(user, session)
    entries = _entries_for(user.id, session)
    days = program.build_days(enrolled_on, entries)

    return WeeksResponse(
        weeks=program.build_weeks(days), summary=program.summarise(enrolled_on, entries)
    )


@router.put("/days/{day_number}", status_code=status.HTTP_200_OK)
def upsert_day(
    day_number: int,
    payload: ActivityUpsert,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    if user.role != Role.student:
        raise HTTPException(403, "The activity programme is for students.")

    if not 1 <= day_number <= settings.program_days:
        raise HTTPException(404, f"Day {day_number} is not part of this programme.")

    enrolled_on = _ensure_enrolled(user, session)
    current = program.current_day_number(enrolled_on)

    # The date lock lives here, not in the UI. A hidden button is not a rule.
    if day_number > current:
        opens_on = program.date_for_day(enrolled_on, day_number)
        raise HTTPException(
            403, f"Day {day_number} unlocks on {opens_on.isoformat()}."
        )
    if day_number < current:
        raise HTTPException(
            403,
            f"Day {day_number} closed when its date passed. You can only submit day {current}.",
        )

    entry = session.exec(
        select(DailyActivity)
        .where(DailyActivity.student_id == user.id)
        .where(DailyActivity.day_number == day_number)
    ).first()

    if entry is None:
        entry = DailyActivity(
            student_id=user.id,
            day_number=day_number,
            activity_date=program.date_for_day(enrolled_on, day_number),
        )

    entry.status = ActivityStatus(payload.status)
    entry.notes = payload.notes.strip()
    entry.hours = payload.hours
    entry.link = (payload.link or "").strip() or None
    entry.updated_at = utcnow()

    session.add(entry)
    session.commit()
    session.refresh(entry)

    entries = _entries_for(user.id, session)
    return {
        "day": next(
            d
            for d in program.build_days(enrolled_on, entries)
            if d["day_number"] == day_number
        ),
        "summary": program.summarise(enrolled_on, entries),
    }
