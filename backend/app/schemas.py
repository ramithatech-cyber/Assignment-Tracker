"""Request / response models.

`frontend/src/types.ts` mirrors this file -- keep the two in step.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models import Role, SubmissionStatus


# --------------------------------------------------------------------------- auth
class UserCreate(BaseModel):
    email: EmailStr
    # bcrypt inputs are pre-hashed, so long passwords are fine; the floor is
    # what actually matters.
    password: str = Field(min_length=8, max_length=200)
    full_name: str = Field(min_length=1, max_length=120)
    role: Role = Role.student


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: int
    email: str
    full_name: str
    role: Role
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


# --------------------------------------------------------------------- assignments
class AssignmentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    requirements: str = ""
    due_date: Optional[datetime] = None


class AssignmentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    requirements: Optional[str] = None
    due_date: Optional[datetime] = None
    is_open: Optional[bool] = None


class AssignmentRead(BaseModel):
    id: int
    teacher_id: int
    title: str
    description: str
    requirements: str
    due_date: Optional[datetime]
    is_open: bool
    created_at: datetime
    teacher_name: Optional[str] = None
    submission_count: int = 0
    my_submission_id: Optional[int] = None

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------- submissions
class SubmissionCreate(BaseModel):
    assignment_id: int
    repo_url: str = Field(min_length=1, max_length=500)

    @field_validator("repo_url")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class CategoryScore(BaseModel):
    key: str
    label: str
    score: float
    max_score: float
    justification: str


class Strength(BaseModel):
    title: str
    detail: str
    file: Optional[str] = None


class Improvement(BaseModel):
    title: str
    detail: str
    suggestion: str
    severity: str  # low | medium | high
    file: Optional[str] = None


class ReportRead(BaseModel):
    summary: str
    category_scores: list[CategoryScore]
    strengths: list[Strength]
    improvements: list[Improvement]
    static_metrics: dict[str, Any]
    applied_caps: list[str]
    llm_model: str
    tokens_used: int
    duration_ms: int

    model_config = {"from_attributes": True}


# -------------------------------------------------------------- 45-day programme
class ActivityUpsert(BaseModel):
    status: str = Field(default="completed", pattern="^(completed|partial|skipped)$")
    notes: str = Field(default="", max_length=4000)
    hours: float = Field(default=0.0, ge=0, le=24)
    link: Optional[str] = Field(default=None, max_length=500)


class DaysResponse(BaseModel):
    days: list[dict[str, Any]]
    summary: dict[str, Any]


class WeeksResponse(BaseModel):
    weeks: list[dict[str, Any]]
    summary: dict[str, Any]


class SubmissionRead(BaseModel):
    id: int
    assignment_id: int
    student_id: int
    repo_url: str
    repo_owner: str
    repo_name: str
    default_branch: str
    commit_sha: str
    status: SubmissionStatus
    error_message: Optional[str]
    total_score: Optional[float]
    grade: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    student_name: Optional[str] = None
    assignment_title: Optional[str] = None
    report: Optional[ReportRead] = None

    model_config = {"from_attributes": True}
