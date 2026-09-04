from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.auth import get_current_user, require_teacher
from app.database import get_session
from app.models import Assignment, Role, Submission, User
from app.schemas import AssignmentCreate, AssignmentRead, AssignmentUpdate, SubmissionRead

router = APIRouter(prefix="/api/assignments", tags=["assignments"])


def _to_read(
    assignment: Assignment, session: Session, viewer: User
) -> AssignmentRead:
    teacher = session.get(User, assignment.teacher_id)
    submissions = session.exec(
        select(Submission).where(Submission.assignment_id == assignment.id)
    ).all()

    mine = None
    if viewer.role == Role.student:
        own = [s for s in submissions if s.student_id == viewer.id]
        if own:
            mine = max(own, key=lambda s: s.created_at).id

    return AssignmentRead(
        id=assignment.id,
        teacher_id=assignment.teacher_id,
        title=assignment.title,
        description=assignment.description,
        requirements=assignment.requirements,
        due_date=assignment.due_date,
        is_open=assignment.is_open,
        created_at=assignment.created_at,
        teacher_name=teacher.full_name if teacher else None,
        submission_count=len(submissions),
        my_submission_id=mine,
    )


def _get_or_404(assignment_id: int, session: Session) -> Assignment:
    assignment = session.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    return assignment


@router.get("", response_model=list[AssignmentRead])
def list_assignments(
    user: User = Depends(get_current_user), session: Session = Depends(get_session)
) -> list[AssignmentRead]:
    statement = select(Assignment).order_by(Assignment.created_at.desc())
    if user.role == Role.teacher:
        statement = statement.where(Assignment.teacher_id == user.id)
    return [_to_read(a, session, user) for a in session.exec(statement).all()]


@router.post("", response_model=AssignmentRead, status_code=status.HTTP_201_CREATED)
def create_assignment(
    payload: AssignmentCreate,
    teacher: User = Depends(require_teacher),
    session: Session = Depends(get_session),
) -> AssignmentRead:
    assignment = Assignment(teacher_id=teacher.id, **payload.model_dump())
    session.add(assignment)
    session.commit()
    session.refresh(assignment)
    return _to_read(assignment, session, teacher)


@router.get("/{assignment_id}", response_model=AssignmentRead)
def get_assignment(
    assignment_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AssignmentRead:
    assignment = _get_or_404(assignment_id, session)
    if user.role == Role.teacher and assignment.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="This is not your assignment.")
    return _to_read(assignment, session, user)


@router.patch("/{assignment_id}", response_model=AssignmentRead)
def update_assignment(
    assignment_id: int,
    payload: AssignmentUpdate,
    teacher: User = Depends(require_teacher),
    session: Session = Depends(get_session),
) -> AssignmentRead:
    assignment = _get_or_404(assignment_id, session)
    if assignment.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail="This is not your assignment.")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(assignment, key, value)
    session.add(assignment)
    session.commit()
    session.refresh(assignment)
    return _to_read(assignment, session, teacher)


@router.get("/{assignment_id}/submissions", response_model=list[SubmissionRead])
def list_submissions(
    assignment_id: int,
    teacher: User = Depends(require_teacher),
    session: Session = Depends(get_session),
) -> list[SubmissionRead]:
    assignment = _get_or_404(assignment_id, session)
    if assignment.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail="This is not your assignment.")

    submissions = session.exec(
        select(Submission)
        .where(Submission.assignment_id == assignment_id)
        .order_by(Submission.created_at.desc())
    ).all()

    rows: list[SubmissionRead] = []
    for submission in submissions:
        student = session.get(User, submission.student_id)
        row = SubmissionRead.model_validate(submission)
        row.student_name = student.full_name if student else None
        row.assignment_title = assignment.title
        row.report = None  # keep the table payload light; open one to see detail
        rows.append(row)
    return rows
