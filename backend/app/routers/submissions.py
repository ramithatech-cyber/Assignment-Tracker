import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session, select

from app.auth import get_current_user
from app.database import get_session
from app.models import (
    AnalysisReport,
    Assignment,
    Role,
    Submission,
    SubmissionStatus,
    User,
    utcnow,
)
from app.rate_limit import limiter
from app.schemas import ReportRead, SubmissionCreate, SubmissionRead
from app.services.errors import AnalysisError
from app.services.pipeline import run_analysis

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/submissions", tags=["submissions"])


def _hydrate(submission: Submission, session: Session) -> SubmissionRead:
    row = SubmissionRead.model_validate(submission)
    student = session.get(User, submission.student_id)
    assignment = session.get(Assignment, submission.assignment_id)
    row.student_name = student.full_name if student else None
    row.assignment_title = assignment.title if assignment else None

    report = session.exec(
        select(AnalysisReport).where(AnalysisReport.submission_id == submission.id)
    ).first()
    row.report = ReportRead.model_validate(report) if report else None
    return row


@router.post("", response_model=SubmissionRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
def create_submission(
    request: Request,
    payload: SubmissionCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SubmissionRead:
    """Analyse a repository and return the finished report.

    This runs the whole pipeline inline, so the request is long-lived (roughly
    30-120 seconds). `run_analysis` is a plain function with no request state in
    it, so moving this onto a worker later is a change to this handler alone.
    """
    assignment = session.get(Assignment, payload.assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    if not assignment.is_open and user.role == Role.student:
        raise HTTPException(status_code=403, detail="This assignment is closed for submissions.")

    submission = Submission(
        assignment_id=assignment.id,
        student_id=user.id,
        repo_url=payload.repo_url,
        status=SubmissionStatus.analyzing,
    )
    session.add(submission)
    session.commit()
    session.refresh(submission)

    try:
        result = run_analysis(
            payload.repo_url, assignment.title, assignment.requirements
        )
    except AnalysisError as exc:
        submission.status = SubmissionStatus.failed
        submission.error_message = exc.message
        submission.completed_at = utcnow()
        session.add(submission)
        session.commit()
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as exc:  # noqa: BLE001 - the failure must be recorded, whatever it is
        log.exception("Unexpected failure analysing %s", payload.repo_url)
        submission.status = SubmissionStatus.failed
        submission.error_message = "An unexpected error occurred during analysis."
        submission.completed_at = utcnow()
        session.add(submission)
        session.commit()
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred during analysis."
        ) from exc

    submission.repo_owner = result.repo_owner
    submission.repo_name = result.repo_name
    submission.default_branch = result.default_branch
    submission.commit_sha = result.commit_sha
    submission.total_score = result.total_score
    submission.grade = result.grade
    submission.status = SubmissionStatus.completed
    submission.error_message = None
    submission.completed_at = utcnow()

    report = AnalysisReport(
        submission_id=submission.id,
        summary=result.summary,
        category_scores=result.category_scores,
        strengths=result.strengths,
        improvements=result.improvements,
        static_metrics=result.static_metrics,
        applied_caps=result.applied_caps,
        llm_model=result.llm_model,
        tokens_used=result.tokens_used,
        duration_ms=result.duration_ms,
    )
    session.add(submission)
    session.add(report)
    session.commit()
    session.refresh(submission)

    return _hydrate(submission, session)


@router.get("/me", response_model=list[SubmissionRead])
def my_submissions(
    user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> list[SubmissionRead]:
    submissions = session.exec(
        select(Submission)
        .where(Submission.student_id == user.id)
        .order_by(Submission.created_at.desc())
    ).all()
    rows = []
    for submission in submissions:
        row = SubmissionRead.model_validate(submission)
        assignment = session.get(Assignment, submission.assignment_id)
        row.assignment_title = assignment.title if assignment else None
        row.student_name = user.full_name
        rows.append(row)
    return rows


@router.get("/{submission_id}", response_model=SubmissionRead)
def get_submission(
    submission_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SubmissionRead:
    submission = session.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found.")

    # Ownership is enforced here, not in the UI: a student sees only their own
    # work, a teacher only submissions against assignments they own.
    if user.role == Role.student:
        allowed = submission.student_id == user.id
    else:
        assignment = session.get(Assignment, submission.assignment_id)
        allowed = assignment is not None and assignment.teacher_id == user.id

    if not allowed:
        raise HTTPException(
            status_code=403, detail="You do not have access to this submission."
        )

    return _hydrate(submission, session)
