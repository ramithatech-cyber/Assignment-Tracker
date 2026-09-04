"""The overall student remark: context building, caching, and staleness."""

from datetime import timedelta

import pytest
from sqlmodel import Session, select

from app.database import engine
from app.models import StudentRemark, User
from app.services import program, remark
from tests.conftest import auth

FAKE_REMARK = {
    "summary": "Grace writes clean code but has never shipped a test file.",
    "trajectory": "improving",
    "strengths": ["Consistent naming", "Clear module boundaries"],
    "concerns": ["No automated tests in any submission", "Sparse README"],
    "recommendation": "Write tests for the core parser before the next submission.",
}


@pytest.fixture()
def stub_llm(monkeypatch):
    calls = {"count": 0}

    def _generate(context: str):
        calls["count"] += 1
        calls["last_context"] = context
        return FAKE_REMARK, 1234

    monkeypatch.setattr("app.routers.admin.remark.generate", _generate)
    return calls


def _submit(client, teacher, student):
    """Create one completed submission. Requires `stub_pipeline` to be active."""
    assignment = client.post(
        "/api/assignments",
        json={"title": "Scraper", "requirements": "Scrape and store."},
        headers=auth(teacher["access_token"]),
    ).json()

    return client.post(
        "/api/submissions",
        json={"assignment_id": assignment["id"], "repo_url": "https://github.com/psf/requests"},
        headers=auth(student["access_token"]),
    )


@pytest.fixture()
def stub_pipeline(monkeypatch):
    """Replace the repo-analysis pipeline so submissions cost nothing."""
    from tests.test_api import FAKE_RESULT

    monkeypatch.setattr(
        "app.routers.submissions.run_analysis", lambda *a, **k: FAKE_RESULT
    )


def _enrol(student_id: int, days_ago: int) -> None:
    with Session(engine) as session:
        user = session.get(User, student_id)
        user.enrolled_on = program.program_today() - timedelta(days=days_ago)
        session.add(user)
        session.commit()


# ------------------------------------------------------------------- context
def test_context_includes_scores_findings_and_daily_stats():
    performance = {
        "submission_count": 2,
        "failed_count": 0,
        "average_score": 68.0,
        "best_score": 80.0,
        "performance_level": "On track",
        "performance_index": 62.0,
        "programme": {
            "current_day": 10, "total_days": 45, "submitted_days": 7,
            "elapsed_days": 10, "missed_days": 3, "completion": 0.7,
            "current_streak": 4, "total_hours": 22.5,
        },
    }
    submissions = [
        {
            "assignment_title": "Scraper", "assignment_id": 1, "total_score": 80.0,
            "grade": "B", "status": "completed", "repo_url": "https://github.com/g/two",
            "created_at": "2026-02-01T00:00:00",
            "report": {
                "summary": "Better structured than the first attempt.",
                "category_scores": [
                    {"label": "Testing", "score": 2.0, "max_score": 10.0},
                ],
                "strengths": [{"title": "Good module split"}],
                "improvements": [{"title": "Still no tests", "severity": "high"}],
                "applied_caps": ["No test files found anywhere in the repository."],
            },
        },
        {
            "assignment_title": "Parser", "assignment_id": 2, "total_score": 56.0,
            "grade": "F", "status": "completed", "repo_url": "https://github.com/g/one",
            "created_at": "2026-01-01T00:00:00",
            "report": {"summary": "A first attempt.", "category_scores": [],
                       "strengths": [], "improvements": [], "applied_caps": []},
        },
    ]

    context = remark.build_context("Grace Hopper", performance, submissions)

    assert "Grace Hopper" in context
    assert "Average score: 68.0" in context
    assert "70% consistency" in context
    assert "Still no tests" in context
    assert "No test files found" in context
    # Oldest first, so any trend reads in the natural direction.
    assert context.index("Parser") < context.index("Scraper")


def test_context_is_honest_when_nothing_is_graded():
    performance = {
        "submission_count": 0, "failed_count": 0, "average_score": None,
        "best_score": None, "performance_level": "No data", "performance_index": None,
        "programme": {
            "current_day": 1, "total_days": 45, "submitted_days": 0, "elapsed_days": 1,
            "missed_days": 0, "completion": 0.0, "current_streak": 0, "total_hours": 0,
        },
    }
    context = remark.build_context("New Student", performance, [])
    assert "no graded submissions" in context
    assert "(none analysed successfully yet)" in context


# ----------------------------------------------------------------- staleness
def test_staleness_detection():
    record = StudentRemark(student_id=1, based_on_submissions=2, based_on_days=5)

    assert remark.is_stale(record, 2, 5) is None
    assert remark.is_stale(record, 3, 5) == "1 new submission"
    assert remark.is_stale(record, 2, 8) == "3 new daily entries"
    assert remark.is_stale(record, 4, 6) == "2 new submissions and 1 new daily entry"
    assert remark.is_stale(None, 9, 9) is None


# ------------------------------------------------------------------ endpoint
def test_detail_has_no_remark_until_one_is_generated(client, teacher, student):
    body = client.get(
        f"/api/admin/students/{student['user']['id']}",
        headers=auth(teacher["access_token"]),
    ).json()
    assert body["remark"] is None


def test_generate_and_cache_a_remark(client, teacher, student, stub_llm):
    student_id = student["user"]["id"]
    headers = auth(teacher["access_token"])

    # Give the student something to be remarked upon.
    _enrol(student_id, days_ago=1)  # today is day 2
    client.put(
        "/api/activities/days/2",
        headers=auth(student["access_token"]),
        json={"status": "completed", "notes": "worked on the parser", "hours": 3},
    )

    created = client.post(f"/api/admin/students/{student_id}/remark", headers=headers)
    assert created.status_code == 200, created.text
    body = created.json()

    assert body["summary"] == FAKE_REMARK["summary"]
    assert body["trajectory"] == "improving"
    assert body["concerns"][0] == "No automated tests in any submission"
    assert body["based_on_days"] == 1
    assert body["tokens_used"] == 1234
    assert stub_llm["count"] == 1

    # It is cached: reading the detail page must not spend another call.
    detail = client.get(f"/api/admin/students/{student_id}", headers=headers).json()
    assert detail["remark"]["summary"] == FAKE_REMARK["summary"]
    assert detail["remark"]["stale_reason"] is None
    assert stub_llm["count"] == 1


def test_remark_goes_stale_when_new_work_arrives(
    client, teacher, student, stub_llm, stub_pipeline
):
    student_id = student["user"]["id"]
    headers = auth(teacher["access_token"])
    _enrol(student_id, days_ago=1)  # today is day 2

    # Remark is written off one submission and zero daily entries...
    _submit(client, teacher, student)
    client.post(f"/api/admin/students/{student_id}/remark", headers=headers)

    # ...then the student files a day, so the verdict is out of date.
    client.put(
        "/api/activities/days/2",
        headers=auth(student["access_token"]),
        json={"status": "completed", "notes": "new work", "hours": 2},
    )

    detail = client.get(f"/api/admin/students/{student_id}", headers=headers).json()
    assert detail["remark"]["stale_reason"] == "1 new daily entry"


def test_regenerating_overwrites_rather_than_duplicating(client, teacher, student, stub_llm):
    student_id = student["user"]["id"]
    headers = auth(teacher["access_token"])

    _enrol(student_id, days_ago=0)  # today is day 1
    client.put(
        "/api/activities/days/1",
        headers=auth(student["access_token"]),
        json={"status": "completed", "notes": "something to judge", "hours": 1},
    )

    client.post(f"/api/admin/students/{student_id}/remark", headers=headers)
    client.post(f"/api/admin/students/{student_id}/remark", headers=headers)

    assert stub_llm["count"] == 2
    with Session(engine) as session:
        records = session.exec(
            select(StudentRemark).where(StudentRemark.student_id == student_id)
        ).all()
    assert len(records) == 1


def test_a_student_with_nothing_gets_a_clear_refusal(client, teacher, student, stub_llm):
    response = client.post(
        f"/api/admin/students/{student['user']['id']}/remark",
        headers=auth(teacher["access_token"]),
    )
    assert response.status_code == 422
    assert "nothing to write a remark about" in response.json()["detail"]
    assert stub_llm["count"] == 0  # no wasted OpenAI call


def test_students_cannot_generate_remarks(client, student, stub_llm):
    response = client.post(
        f"/api/admin/students/{student['user']['id']}/remark",
        headers=auth(student["access_token"]),
    )
    assert response.status_code == 403
    assert stub_llm["count"] == 0


def test_detail_submissions_now_include_their_reports(
    client, teacher, student, stub_pipeline
):
    _submit(client, teacher, student)

    body = client.get(
        f"/api/admin/students/{student['user']['id']}",
        headers=auth(teacher["access_token"]),
    ).json()

    assert len(body["submissions"]) == 1
    assert body["submissions"][0]["report"]["summary"].startswith("A solid submission")
