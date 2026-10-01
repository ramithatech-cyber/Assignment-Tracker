"""Test fixtures.

The environment is set before `app` is imported anywhere, because settings is a
cached singleton read at import time.
"""

import os
import sys
import tempfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

_db_file = Path(tempfile.gettempdir()) / "assignment_tracker_test.db"
_db_file.unlink(missing_ok=True)

os.environ["DATABASE_URL"] = f"sqlite:///{_db_file.as_posix()}"
os.environ["JWT_SECRET"] = "test-secret-not-used-anywhere-real"
os.environ["OPENAI_API_KEY"] = ""
os.environ["ADMIN_SIGNUP_CODE"] = "test-admin-code"

ADMIN_SIGNUP_CODE = "test-admin-code"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

from app import models  # noqa: E402,F401 - registers the tables
from app.database import engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_database():
    """Every test starts from an empty schema, so tests never leak state."""
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield


@pytest.fixture(scope="session", autouse=True)
def _teardown():
    yield
    engine.dispose()
    _db_file.unlink(missing_ok=True)


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def teacher(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "teacher@example.com",
            "password": "correct-horse-battery",
            "full_name": "Ada Teacher",
            "role": "teacher",
            "signup_code": ADMIN_SIGNUP_CODE,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture()
def student(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "student@example.com",
            "password": "correct-horse-battery",
            "full_name": "Grace Student",
            "role": "student",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
