"""Database tables.

Note: no `from __future__ import annotations` here. SQLModel resolves
relationship targets from the live annotation object, and stringifying every
annotation breaks mapper configuration.
"""

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Optional

from sqlalchemy import JSON, Column, Text, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Role(str, Enum):
    student = "student"
    teacher = "teacher"


class SubmissionStatus(str, Enum):
    pending = "pending"
    analyzing = "analyzing"
    completed = "completed"
    failed = "failed"


class ActivityStatus(str, Enum):
    completed = "completed"
    partial = "partial"
    skipped = "skipped"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True, max_length=255)
    hashed_password: str = Field(max_length=255)
    full_name: str = Field(max_length=120)
    role: Role = Field(default=Role.student, index=True)
    created_at: datetime = Field(default_factory=utcnow)

    # Day 1 of the 45-day activity programme. Defaults to the registration date;
    # every day/lock calculation is relative to this.
    enrolled_on: Optional[date] = Field(default=None)

    assignments: list["Assignment"] = Relationship(back_populates="teacher")
    submissions: list["Submission"] = Relationship(back_populates="student")
    activities: list["DailyActivity"] = Relationship(back_populates="student")


class Assignment(SQLModel, table=True):
    __tablename__ = "assignments"

    id: Optional[int] = Field(default=None, primary_key=True)
    teacher_id: int = Field(foreign_key="users.id", index=True)
    title: str = Field(max_length=200)
    description: str = Field(default="", sa_column=Column(Text))
    # The grading brief handed verbatim to the model as "what was asked for".
    requirements: str = Field(default="", sa_column=Column(Text))
    due_date: Optional[datetime] = None
    is_open: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utcnow)

    teacher: Optional[User] = Relationship(back_populates="assignments")
    submissions: list["Submission"] = Relationship(
        back_populates="assignment",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Submission(SQLModel, table=True):
    __tablename__ = "submissions"

    id: Optional[int] = Field(default=None, primary_key=True)
    assignment_id: int = Field(foreign_key="assignments.id", index=True)
    student_id: int = Field(foreign_key="users.id", index=True)

    repo_url: str = Field(max_length=500)
    repo_owner: str = Field(default="", max_length=120)
    repo_name: str = Field(default="", max_length=120)
    default_branch: str = Field(default="", max_length=120)
    commit_sha: str = Field(default="", max_length=64)

    # `status` / `error_message` exist from day one so moving the pipeline to a
    # background worker later needs no schema migration.
    status: SubmissionStatus = Field(default=SubmissionStatus.pending, index=True)
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))

    total_score: Optional[float] = Field(default=None, index=True)
    grade: Optional[str] = Field(default=None, max_length=4)

    created_at: datetime = Field(default_factory=utcnow)
    completed_at: Optional[datetime] = None

    assignment: Optional[Assignment] = Relationship(back_populates="submissions")
    student: Optional[User] = Relationship(back_populates="submissions")
    report: Optional["AnalysisReport"] = Relationship(
        back_populates="submission",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "uselist": False},
    )


class AnalysisReport(SQLModel, table=True):
    __tablename__ = "analysis_reports"

    id: Optional[int] = Field(default=None, primary_key=True)
    submission_id: int = Field(foreign_key="submissions.id", unique=True, index=True)

    summary: str = Field(default="", sa_column=Column(Text))
    category_scores: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    strengths: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    improvements: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    static_metrics: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    applied_caps: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    llm_model: str = Field(default="", max_length=80)
    tokens_used: int = Field(default=0)
    duration_ms: int = Field(default=0)
    created_at: datetime = Field(default_factory=utcnow)

    submission: Optional[Submission] = Relationship(back_populates="report")


class StudentRemark(SQLModel, table=True):
    """An admin-facing overall verdict on one student's whole body of work.

    Cached: generating it costs an OpenAI call, so it is written once and reused
    until an admin explicitly regenerates it.
    """

    __tablename__ = "student_remarks"

    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="users.id", unique=True, index=True)

    summary: str = Field(default="", sa_column=Column(Text))
    trajectory: str = Field(default="steady", max_length=32)
    strengths: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    concerns: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    recommendation: str = Field(default="", sa_column=Column(Text))

    # What the verdict was based on, so a stale remark is obvious.
    based_on_submissions: int = Field(default=0)
    based_on_days: int = Field(default=0)
    performance_level: str = Field(default="", max_length=32)

    llm_model: str = Field(default="", max_length=80)
    tokens_used: int = Field(default=0)
    generated_at: datetime = Field(default_factory=utcnow)
    generated_by_id: Optional[int] = Field(default=None, foreign_key="users.id")


class DailyActivity(SQLModel, table=True):
    """One day of the 45-day activity programme, for one student."""

    __tablename__ = "daily_activities"
    __table_args__ = (UniqueConstraint("student_id", "day_number", name="uq_student_day"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="users.id", index=True)
    day_number: int = Field(index=True)  # 1..PROGRAM_DAYS

    # The calendar date this day represents, derived from the student's
    # enrolment date. Stored so a later change of enrolment date cannot silently
    # rewrite history.
    activity_date: date

    status: ActivityStatus = Field(default=ActivityStatus.completed)
    notes: str = Field(default="", sa_column=Column(Text))
    hours: float = Field(default=0.0)
    link: Optional[str] = Field(default=None, max_length=500)

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    student: Optional[User] = Relationship(back_populates="activities")
