"""The admin dashboard: student performance levels and access control."""

from datetime import timedelta

from sqlmodel import Session, select

from app.database import engine
from app.models import User
from app.services import performance, program
from tests.conftest import auth


def test_performance_index_blends_score_and_consistency():
    # 90 score, 50% consistency -> 0.6*90 + 0.4*50
    assert performance.performance_index(90, 0.5) == 74.0
    # Only one signal available: use it alone rather than scoring the gap as 0.
    assert performance.performance_index(90, None) == 90.0
    assert performance.performance_index(None, 0.8) == 80.0
    assert performance.performance_index(None, None) is None


def test_performance_levels_band_correctly():
    assert performance.level_for(92)[0] == "Excellent"
    assert performance.level_for(75)[0] == "Strong"
    assert performance.level_for(60)[0] == "On track"
    assert performance.level_for(45)[0] == "Needs support"
    assert performance.level_for(10)[0] == "At risk"
    assert performance.level_for(None)[0] == "No data"


def test_students_list_requires_an_admin(client, student, teacher):
    denied = client.get("/api/admin/students", headers=auth(student["access_token"]))
    assert denied.status_code == 403

    allowed = client.get("/api/admin/students", headers=auth(teacher["access_token"]))
    assert allowed.status_code == 200


def test_student_row_reflects_daily_activity(client, student, teacher):
    # Backdate so day 3 is today, then file one day.
    enrolled = program.program_today() - timedelta(days=2)
    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.email == "student@example.com")
        ).first()
        user.enrolled_on = enrolled
        session.add(user)
        session.commit()

    client.put(
        "/api/activities/days/3",
        headers=auth(student["access_token"]),
        json={"status": "completed", "notes": "did the thing", "hours": 4},
    )

    rows = client.get("/api/admin/students", headers=auth(teacher["access_token"])).json()
    row = next(r for r in rows if r["email"] == "student@example.com")

    assert row["student_name"] == "Grace Student"
    assert row["programme"]["submitted_days"] == 1
    assert row["programme"]["elapsed_days"] == 3
    assert row["programme"]["total_hours"] == 4.0
    # No graded submissions yet, so the level rests on consistency alone.
    assert row["average_score"] is None
    assert row["performance_index"] == round(1 / 3 * 100, 1)


def test_overview_aggregates(client, student, teacher):
    body = client.get("/api/admin/overview", headers=auth(teacher["access_token"])).json()

    assert body["students"] == 1
    assert "distribution" in body
    assert isinstance(body["top_performers"], list)


def test_student_detail_includes_submissions_and_weeks(client, student, teacher):
    body = client.get(
        f"/api/admin/students/{student['user']['id']}",
        headers=auth(teacher["access_token"]),
    ).json()

    assert body["performance"]["student_name"] == "Grace Student"
    assert len(body["weeks"]) == 7
    assert isinstance(body["submissions"], list)


def test_student_detail_404s_for_a_teacher_id(client, teacher):
    response = client.get(
        f"/api/admin/students/{teacher['user']['id']}",
        headers=auth(teacher["access_token"]),
    )
    assert response.status_code == 404


def test_a_student_cannot_read_the_dashboard(client, student):
    for path in ("/api/admin/overview", "/api/admin/students"):
        assert client.get(path, headers=auth(student["access_token"])).status_code == 403
