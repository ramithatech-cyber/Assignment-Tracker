"""End-to-end API behaviour with the OpenAI call replaced by a stub.

These tests make no network calls and cost nothing to run.
"""

import pytest

from app.services.errors import AnalysisError
from app.services.pipeline import AnalysisResult
from tests.conftest import auth

FAKE_RESULT = AnalysisResult(
    repo_owner="psf",
    repo_name="requests",
    default_branch="main",
    commit_sha="abc1234",
    summary="A solid submission with good structure but no tests.",
    category_scores=[
        {"key": "code_quality", "label": "Code Quality & Readability", "score": 16.0,
         "max_score": 20.0, "justification": "Clean naming throughout."},
        {"key": "testing", "label": "Testing", "score": 2.0, "max_score": 10.0,
         "justification": "No test files found."},
    ],
    strengths=[{"title": "Clear layout", "detail": "Modules are well separated.",
                "file": "src/main.py", "verified": True}],
    improvements=[{"title": "Add tests", "detail": "There are none.",
                   "suggestion": "Start with the parser.", "severity": "high",
                   "file": "src/main.py", "verified": True}],
    static_metrics={"total_loc": 900, "tests": {"count": 0}},
    applied_caps=["No test files found anywhere in the repository (Testing capped at 2/10)."],
    total_score=71.5,
    grade="C",
    llm_model="stub",
    tokens_used=1234,
    duration_ms=4200,
)


@pytest.fixture()
def stub_analysis(monkeypatch):
    def _run(repo_url, title, requirements):
        return FAKE_RESULT

    monkeypatch.setattr("app.routers.submissions.run_analysis", _run)


# ------------------------------------------------------------------------ auth
def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_register_login_and_me(client, student):
    token = student["access_token"]
    assert client.get("/api/auth/me", headers=auth(token)).json()["role"] == "student"

    duplicate = client.post(
        "/api/auth/register",
        json={"email": "student@example.com", "password": "another-password",
              "full_name": "Impostor", "role": "student"},
    )
    assert duplicate.status_code == 409

    ok = client.post("/api/auth/login",
                     json={"email": "student@example.com", "password": "correct-horse-battery"})
    assert ok.status_code == 200

    bad = client.post("/api/auth/login",
                      json={"email": "student@example.com", "password": "wrong"})
    assert bad.status_code == 401


ADMIN_PAYLOAD = {"email": "new.admin@example.com", "password": "correct-horse-battery",
                 "full_name": "New Admin", "role": "teacher"}


@pytest.mark.parametrize("code", [None, "", "wrong-code"])
def test_admin_registration_requires_the_signup_code(client, code):
    payload = dict(ADMIN_PAYLOAD, signup_code=code) if code is not None else ADMIN_PAYLOAD
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid admin signup code."

    # No account is created, so the email is still free.
    login = client.post("/api/auth/login", json={"email": ADMIN_PAYLOAD["email"],
                                                 "password": ADMIN_PAYLOAD["password"]})
    assert login.status_code == 401


def test_admin_registration_with_the_signup_code(client):
    response = client.post("/api/auth/register",
                           json=dict(ADMIN_PAYLOAD, signup_code="test-admin-code"))
    assert response.status_code == 201
    assert response.json()["user"]["role"] == "teacher"


def test_admin_registration_is_disabled_without_a_configured_code(client, monkeypatch):
    monkeypatch.setattr("app.routers.auth.settings.admin_signup_code", "")
    response = client.post("/api/auth/register", json=dict(ADMIN_PAYLOAD, signup_code=""))
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin registration is disabled on this server."


def test_student_registration_needs_no_signup_code(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "s2@example.com", "password": "correct-horse-battery",
              "full_name": "Second Student", "role": "student"},
    )
    assert response.status_code == 201
    assert response.json()["user"]["role"] == "student"


def test_protected_routes_require_a_token(client):
    assert client.get("/api/assignments").status_code == 401
    assert client.get("/api/auth/me", headers=auth("garbage.token.here")).status_code == 401


# ----------------------------------------------------------------- assignments
def test_only_teachers_can_create_assignments(client, teacher, student):
    payload = {"title": "Build a REST API", "description": "Any framework.",
               "requirements": "CRUD endpoints, tests, README."}

    denied = client.post("/api/assignments", json=payload,
                         headers=auth(student["access_token"]))
    assert denied.status_code == 403

    created = client.post("/api/assignments", json=payload,
                          headers=auth(teacher["access_token"]))
    assert created.status_code == 201
    assert created.json()["teacher_name"] == "Ada Teacher"


def test_students_see_all_assignments(client, teacher, student):
    client.post("/api/assignments",
                json={"title": "Sorting algorithms", "requirements": "Implement quicksort."},
                headers=auth(teacher["access_token"]))
    visible = client.get("/api/assignments", headers=auth(student["access_token"])).json()
    assert any(a["title"] == "Sorting algorithms" for a in visible)


# ----------------------------------------------------------------- submissions
def test_submission_stores_score_and_report(client, teacher, student, stub_analysis):
    assignment = client.post(
        "/api/assignments",
        json={"title": "Scraper", "requirements": "Scrape and store."},
        headers=auth(teacher["access_token"]),
    ).json()

    response = client.post(
        "/api/submissions",
        json={"assignment_id": assignment["id"], "repo_url": "https://github.com/psf/requests"},
        headers=auth(student["access_token"]),
    )
    assert response.status_code == 201, response.text
    body = response.json()

    assert body["status"] == "completed"
    assert body["total_score"] == 71.5
    assert body["grade"] == "C"
    assert body["repo_owner"] == "psf"
    assert body["report"]["summary"].startswith("A solid submission")
    assert body["report"]["improvements"][0]["severity"] == "high"
    assert body["report"]["applied_caps"]


def test_failed_analysis_is_recorded_not_swallowed(client, teacher, student, monkeypatch):
    def _boom(repo_url, title, requirements):
        raise AnalysisError("Repository psf/nope was not found.", status_code=404)

    monkeypatch.setattr("app.routers.submissions.run_analysis", _boom)

    assignment = client.post(
        "/api/assignments", json={"title": "Broken", "requirements": "x"},
        headers=auth(teacher["access_token"]),
    ).json()

    response = client.post(
        "/api/submissions",
        json={"assignment_id": assignment["id"], "repo_url": "https://github.com/psf/nope"},
        headers=auth(student["access_token"]),
    )
    assert response.status_code == 404
    assert "was not found" in response.json()["detail"]

    history = client.get("/api/submissions/me", headers=auth(student["access_token"])).json()
    failed = [s for s in history if s["status"] == "failed"]
    assert failed and failed[0]["error_message"] == "Repository psf/nope was not found."


def test_a_student_cannot_read_another_students_submission(
    client, teacher, student, stub_analysis
):
    assignment = client.post(
        "/api/assignments", json={"title": "Private", "requirements": "x"},
        headers=auth(teacher["access_token"]),
    ).json()

    submission = client.post(
        "/api/submissions",
        json={"assignment_id": assignment["id"], "repo_url": "https://github.com/psf/requests"},
        headers=auth(student["access_token"]),
    ).json()

    intruder = client.post(
        "/api/auth/register",
        json={"email": "nosy@example.com", "password": "correct-horse-battery",
              "full_name": "Nosy Parker", "role": "student"},
    ).json()

    denied = client.get(f"/api/submissions/{submission['id']}",
                        headers=auth(intruder["access_token"]))
    assert denied.status_code == 403

    # The owning teacher can see it.
    allowed = client.get(f"/api/submissions/{submission['id']}",
                         headers=auth(teacher["access_token"]))
    assert allowed.status_code == 200


def test_teacher_sees_the_submissions_table(client, teacher, student, stub_analysis):
    assignment = client.post(
        "/api/assignments", json={"title": "Graded", "requirements": "x"},
        headers=auth(teacher["access_token"]),
    ).json()
    client.post(
        "/api/submissions",
        json={"assignment_id": assignment["id"], "repo_url": "https://github.com/psf/requests"},
        headers=auth(student["access_token"]),
    )

    rows = client.get(f"/api/assignments/{assignment['id']}/submissions",
                      headers=auth(teacher["access_token"])).json()
    assert len(rows) == 1
    assert rows[0]["student_name"] == "Grace Student"
    assert rows[0]["total_score"] == 71.5


def test_a_teacher_cannot_read_another_teachers_assignment(client, teacher, student):
    other = client.post(
        "/api/auth/register",
        json={"email": "other.teacher@example.com", "password": "correct-horse-battery",
              "full_name": "Other Teacher", "role": "teacher",
              "signup_code": "test-admin-code"},
    ).json()
    assignment = client.post(
        "/api/assignments", json={"title": "Mine", "requirements": "x"},
        headers=auth(teacher["access_token"]),
    ).json()

    denied = client.get(f"/api/assignments/{assignment['id']}",
                        headers=auth(other["access_token"]))
    assert denied.status_code == 403


def test_rubric_endpoint_totals_100(client):
    rubric = client.get("/api/rubric").json()
    assert rubric["total_points"] == 100
    assert sum(c["max"] for c in rubric["categories"]) == 100
