"""A private key under tests/ is a fixture, not a breach.

Regression test: the first live run against psf/requests scored Security 0/10
because of the TLS certificates in its test suite.
"""

from pathlib import Path

from app.services.inspector import inspect_repo
from app.services.scoring import RUBRIC, apply_rubric

PRIVATE_KEY = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA\n-----END RSA PRIVATE KEY-----\n"

GENEROUS = [{"key": i["key"], "score": i["max"], "justification": ""} for i in RUBRIC]
BASE_METRICS = {
    "tests": {"count": 5, "ratio": 0.3},
    "readme": {"exists": True, "chars": 3000, "has_setup": True},
    "dependencies": {"unpinned": []},
    "gitignore": {"exists": True},
    "committed_junk": [],
}
GIT = {"available": True, "commit_count": 30, "generic_ratio": 0.0}


def _repo(tmp_path: Path, key_at: str) -> Path:
    root = tmp_path / "repo"
    target = root / key_at
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(PRIVATE_KEY, encoding="utf-8")
    # Enough real code that the "too little to assess" cap stays out of the way;
    # these tests are about credential classification, nothing else.
    (root / "app.py").write_text(
        "\n".join(f"value_{n} = {n}" for n in range(80)), encoding="utf-8"
    )
    return root


def test_key_in_test_fixtures_is_downgraded(tmp_path):
    result = inspect_repo(_repo(tmp_path, "tests/certs/server.key"))
    assert result.secrets == []
    assert len(result.possible_secrets) == 1
    assert result.possible_secrets[0]["fixture"] is True

    _, total, caps = apply_rubric(
        GENEROUS, {**BASE_METRICS, **result.to_metrics()}, GIT, {}
    )
    assert not any("Security" in c for c in caps)


def test_key_in_application_code_is_a_real_leak(tmp_path):
    result = inspect_repo(_repo(tmp_path, "app/secrets/id_rsa"))
    assert len(result.secrets) == 1
    assert result.secrets[0]["file"] == "app/secrets/id_rsa"

    rows, _, caps = apply_rubric(
        GENEROUS, {**BASE_METRICS, **result.to_metrics()}, GIT, {}
    )
    assert next(r for r in rows if r["key"] == "security")["score"] == 0.0
    assert any("Credentials committed" in c for c in caps)


def test_non_code_fixtures_do_not_count_as_tests(tmp_path):
    root = tmp_path / "repo"
    (root / "tests" / "certs").mkdir(parents=True)
    (root / "tests" / "test_real.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")
    for name in ("a.pem", "b.csr", "c.cnf"):
        (root / "tests" / "certs" / name).write_text("fixture data\n", encoding="utf-8")

    result = inspect_repo(root)
    assert result.tests["count"] == 1  # one real test module, not four files
