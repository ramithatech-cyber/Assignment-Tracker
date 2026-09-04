"""The admin dashboard: every student's submissions, performance, and verdict.

"Admin" is the UI name for the `teacher` role -- these endpoints are guarded by
`require_teacher`.
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.auth import require_teacher
from app.config import settings
from app.database import get_session
from app.models import (
    AnalysisReport,
    Assignment,
    DailyActivity,
    Role,
    StudentRemark,
    Submission,
    SubmissionStatus,
    User,
    utcnow,
)
from app.schemas import ReportRead, SubmissionRead
from app.services import performance, program, remark
from app.services.errors import AnalysisError

router = APIRouter(prefix="/api/admin", tags=["admin"])


# --------------------------------------------------------------------- helpers
def _programme_for(student: User, entries: list[DailyActivity]) -> dict[str, Any]:
    enrolled_on = student.enrolled_on or student.created_at.date()
    return program.summarise(enrolled_on, entries)


def _get_student(student_id: int, session: Session) -> User:
    student = session.get(User, student_id)
    if student is None or student.role != Role.student:
        raise HTTPException(404, "Student not found.")
    return student


def _activities(student_id: int, session: Session) -> list[DailyActivity]:
    return list(
        session.exec(
            select(DailyActivity)
            .where(DailyActivity.student_id == student_id)
            .order_by(DailyActivity.day_number)
        ).all()
    )


def _submissions_with_reports(
    student: User, session: Session
) -> list[dict[str, Any]]:
    """Newest first, each with its full report attached."""
    submissions = list(
        session.exec(
            select(Submission)
            .where(Submission.student_id == student.id)
            .order_by(Submission.created_at.desc())
        ).all()
    )

    rows: list[dict[str, Any]] = []
    for submission in submissions:
        row = SubmissionRead.model_validate(submission)
        assignment = session.get(Assignment, submission.assignment_id)
        row.assignment_title = assignment.title if assignment else None
        row.student_name = student.full_name

        report = session.exec(
            select(AnalysisReport).where(AnalysisReport.submission_id == submission.id)
        ).first()
        row.report = ReportRead.model_validate(report) if report else None
        rows.append(row.model_dump(mode="json"))
    return rows


def _performance_for(
    student: User,
    submissions: list[dict[str, Any]],
    entries: list[DailyActivity],
) -> dict[str, Any]:
    scores = [
        s["total_score"]
        for s in submissions
        if s["status"] == SubmissionStatus.completed.value and s["total_score"] is not None
    ]
    timestamps = [s["created_at"] for s in submissions] + [
        a.updated_at.isoformat() for a in entries
    ]
    return performance.build_row(
        student=student,
        scores=scores,
        submission_count=len(submissions),
        failed_count=sum(
            1 for s in submissions if s["status"] == SubmissionStatus.failed.value
        ),
        programme=_programme_for(student, entries),
        last_active=max(timestamps) if timestamps else None,
    )


def _rows(session: Session) -> list[dict[str, Any]]:
    students = list(session.exec(select(User).where(User.role == Role.student)).all())
    submissions = list(session.exec(select(Submission)).all())
    activities = list(session.exec(select(DailyActivity)).all())

    by_student: dict[int, list[Submission]] = {}
    for submission in submissions:
        by_student.setdefault(submission.student_id, []).append(submission)

    activity_by_student: dict[int, list[DailyActivity]] = {}
    for activity in activities:
        activity_by_student.setdefault(activity.student_id, []).append(activity)

    rows = []
    for student in students:
        own = by_student.get(student.id, [])
        entries = activity_by_student.get(student.id, [])

        scores = [
            s.total_score
            for s in own
            if s.status == SubmissionStatus.completed and s.total_score is not None
        ]
        timestamps = [s.created_at for s in own] + [a.updated_at for a in entries]

        rows.append(
            performance.build_row(
                student=student,
                scores=scores,
                submission_count=len(own),
                failed_count=sum(1 for s in own if s.status == SubmissionStatus.failed),
                programme=_programme_for(student, entries),
                last_active=max(timestamps).isoformat() if timestamps else None,
            )
        )

    rows.sort(key=lambda r: (r["performance_index"] is None, -(r["performance_index"] or 0)))
    return rows


def _remark_payload(record: Optional[StudentRemark], stale: Optional[str]) -> Optional[dict]:
    if record is None:
        return None
    return {
        "summary": record.summary,
        "trajectory": record.trajectory,
        "strengths": record.strengths,
        "concerns": record.concerns,
        "recommendation": record.recommendation,
        "performance_level": record.performance_level,
        "based_on_submissions": record.based_on_submissions,
        "based_on_days": record.based_on_days,
        "llm_model": record.llm_model,
        "tokens_used": record.tokens_used,
        "generated_at": record.generated_at.isoformat(),
        "stale_reason": stale,
    }


# -------------------------------------------------------------------- endpoints
@router.get("/overview")
def overview(
    admin: User = Depends(require_teacher), session: Session = Depends(get_session)
) -> dict[str, Any]:
    rows = _rows(session)

    assignments = list(
        session.exec(select(Assignment).where(Assignment.teacher_id == admin.id)).all()
    )
    scored = [r["average_score"] for r in rows if r["average_score"] is not None]
    completions = [
        r["programme"]["completion"] for r in rows if r["programme"]["elapsed_days"] > 0
    ]

    distribution: dict[str, int] = {}
    for row in rows:
        distribution[row["performance_level"]] = distribution.get(row["performance_level"], 0) + 1

    return {
        "students": len(rows),
        "assignments": len(assignments),
        "submissions": sum(r["submission_count"] for r in rows),
        "average_score": round(sum(scored) / len(scored), 1) if scored else None,
        "average_completion": (
            round(sum(completions) / len(completions), 3) if completions else None
        ),
        "at_risk": sum(
            1 for r in rows if r["performance_level"] in {"At risk", "Needs support"}
        ),
        "distribution": distribution,
        "top_performers": rows[:5],
    }


@router.get("/students")
def students(
    admin: User = Depends(require_teacher), session: Session = Depends(get_session)
) -> list[dict[str, Any]]:
    return _rows(session)


@router.get("/students/{student_id}")
def student_detail(
    student_id: int,
    admin: User = Depends(require_teacher),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    student = _get_student(student_id, session)
    entries = _activities(student_id, session)
    submissions = _submissions_with_reports(student, session)
    enrolled_on = student.enrolled_on or student.created_at.date()
    days = program.build_days(enrolled_on, entries)

    record = session.exec(
        select(StudentRemark).where(StudentRemark.student_id == student_id)
    ).first()
    stale = remark.is_stale(record, len(submissions), len(entries))

    return {
        "performance": _performance_for(student, submissions, entries),
        "submissions": submissions,
        "weeks": program.build_weeks(days),
        "recent_days": [d for d in days if d["entry"]][-10:],
        "remark": _remark_payload(record, stale),
    }


@router.post("/students/{student_id}/remark")
def generate_remark(
    student_id: int,
    admin: User = Depends(require_teacher),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Write (or rewrite) the overall verdict for one student.

    Deliberately a POST behind a button rather than something that runs on page
    load: each call costs an OpenAI request, and an admin scrolling a class of
    thirty should not spend thirty of them.
    """
    student = _get_student(student_id, session)
    entries = _activities(student_id, session)
    submissions = _submissions_with_reports(student, session)

    if not submissions and not entries:
        raise HTTPException(
            422,
            f"{student.full_name} has no submissions and no daily activity yet, "
            "so there is nothing to write a remark about.",
        )

    perf = _performance_for(student, submissions, entries)
    context = remark.build_context(student.full_name, perf, submissions)

    try:
        result, tokens = remark.generate(context)
    except AnalysisError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc

    record = session.exec(
        select(StudentRemark).where(StudentRemark.student_id == student_id)
    ).first()
    if record is None:
        record = StudentRemark(student_id=student_id)

    record.summary = (result.get("summary") or "").strip()
    record.trajectory = result.get("trajectory") or "steady"
    record.strengths = [s for s in (result.get("strengths") or []) if s]
    record.concerns = [c for c in (result.get("concerns") or []) if c]
    record.recommendation = (result.get("recommendation") or "").strip()
    record.based_on_submissions = len(submissions)
    record.based_on_days = len(entries)
    record.performance_level = perf["performance_level"]
    record.llm_model = settings.openai_model
    record.tokens_used = tokens
    record.generated_at = utcnow()
    record.generated_by_id = admin.id

    session.add(record)
    session.commit()
    session.refresh(record)

    return _remark_payload(record, None)
