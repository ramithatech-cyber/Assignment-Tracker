"""The activity endpoints, including the server-side date lock."""

from datetime import date, timedelta

from sqlmodel import Session, select

from app.database import engine
from app.models import User
from app.services import program
from tests.conftest import auth


def _set_enrolment(email: str, days_ago: int) -> date:
    """Backdate a student's day 1 so a given day number is 'today'."""
    enrolled = program.program_today() - timedelta(days=days_ago)
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        user.enrolled_on = enrolled
        session.add(user)
        session.commit()
    return enrolled


def test_days_endpoint_returns_45_days(client, student):
    body = client.get("/api/activities/days", headers=auth(student["access_token"])).json()

    assert len(body["days"]) == 45
    assert body["summary"]["total_days"] == 45
    assert body["days"][0]["day_number"] == 1
    assert body["days"][0]["week"] == 1
    assert body["days"][-1]["week"] == 7


def test_only_the_current_day_is_editable(client, student):
    _set_enrolment("student@example.com", days_ago=4)  # today is day 5
    body = client.get("/api/activities/days", headers=auth(student["access_token"])).json()

    editable = [d["day_number"] for d in body["days"] if d["editable"]]
    assert editable == [5]


def test_submitting_today_works_and_updates_the_summary(client, student):
    _set_enrolment("student@example.com", days_ago=2)  # today is day 3
    headers = auth(student["access_token"])

    response = client.put(
        "/api/activities/days/3",
        headers=headers,
        json={"status": "completed", "notes": "Built the parser", "hours": 3.5,
              "link": "https://github.com/me/project"},
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["day"]["state"] == "submitted"
    assert body["day"]["entry"]["hours"] == 3.5
    assert body["day"]["entry"]["notes"] == "Built the parser"
    assert body["summary"]["submitted_days"] == 1
    assert body["summary"]["total_hours"] == 3.5


def test_resubmitting_the_same_day_updates_rather_than_duplicates(client, student):
    _set_enrolment("student@example.com", days_ago=0)  # today is day 1
    headers = auth(student["access_token"])

    client.put("/api/activities/days/1", headers=headers,
               json={"status": "partial", "notes": "first", "hours": 1})
    second = client.put("/api/activities/days/1", headers=headers,
                        json={"status": "completed", "notes": "revised", "hours": 4})

    assert second.status_code == 200
    assert second.json()["day"]["entry"]["notes"] == "revised"
    assert second.json()["summary"]["submitted_days"] == 1  # not 2


def test_a_future_day_is_rejected(client, student):
    _set_enrolment("student@example.com", days_ago=2)  # today is day 3
    response = client.put(
        "/api/activities/days/10",
        headers=auth(student["access_token"]),
        json={"status": "completed", "notes": "getting ahead", "hours": 1},
    )
    assert response.status_code == 403
    assert "unlocks on" in response.json()["detail"]


def test_a_past_day_is_locked(client, student):
    _set_enrolment("student@example.com", days_ago=6)  # today is day 7
    response = client.put(
        "/api/activities/days/2",
        headers=auth(student["access_token"]),
        json={"status": "completed", "notes": "backfilling", "hours": 1},
    )
    assert response.status_code == 403
    assert "closed when its date passed" in response.json()["detail"]


def test_day_outside_the_programme_is_404(client, student):
    response = client.put(
        "/api/activities/days/99",
        headers=auth(student["access_token"]),
        json={"status": "completed", "notes": "", "hours": 0},
    )
    assert response.status_code == 404


def test_weeks_group_the_days(client, student):
    _set_enrolment("student@example.com", days_ago=9)  # day 10, week 2
    headers = auth(student["access_token"])
    client.put("/api/activities/days/10", headers=headers,
               json={"status": "completed", "notes": "ok", "hours": 2})

    weeks = client.get("/api/activities/weeks", headers=headers).json()["weeks"]
    assert len(weeks) == 7
    assert weeks[0]["day_numbers"] == [1, 2, 3, 4, 5, 6, 7]
    assert weeks[1]["submitted"] == 1
    assert weeks[1]["hours"] == 2.0
    assert weeks[6]["state"] == "upcoming"


def test_admins_have_no_activity_programme(client, teacher):
    response = client.get("/api/activities/days", headers=auth(teacher["access_token"]))
    assert response.status_code == 403
