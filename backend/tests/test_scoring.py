"""The evidence caps -- the part of the grade the model cannot argue with."""

from app.services.scoring import RUBRIC, TOTAL_POINTS, apply_rubric, grade_for

# A model being maximally generous about everything.
GENEROUS = [{"key": item["key"], "score": item["max"], "justification": "Perfect."} for item in RUBRIC]

GOOD_METRICS = {
    "tests": {"count": 12, "ratio": 0.4},
    "readme": {"exists": True, "chars": 3000, "has_setup": True},
    "secrets": [],
    "possible_secrets": [],
    "dependencies": {"unpinned": []},
    "gitignore": {"exists": True},
    "committed_junk": [],
    "total_loc": 2500,
}
GOOD_GIT = {"available": True, "commit_count": 40, "generic_ratio": 0.05}


def test_rubric_sums_to_100():
    assert TOTAL_POINTS == 100


def test_clean_repo_keeps_a_perfect_score():
    rows, total, caps = apply_rubric(GENEROUS, GOOD_METRICS, GOOD_GIT, {})
    assert total == 100.0
    assert caps == []
    assert grade_for(total) == "A"


def test_no_tests_caps_testing_at_two():
    metrics = {**GOOD_METRICS, "tests": {"count": 0, "ratio": 0.0}}
    rows, total, caps = apply_rubric(GENEROUS, metrics, GOOD_GIT, {})
    testing = next(r for r in rows if r["key"] == "testing")
    assert testing["score"] == 2.0
    assert total == 92.0
    assert any("No test files" in c for c in caps)


def test_missing_readme_caps_documentation():
    metrics = {**GOOD_METRICS, "readme": {"exists": False, "chars": 0}}
    rows, _, caps = apply_rubric(GENEROUS, metrics, GOOD_GIT, {})
    assert next(r for r in rows if r["key"] == "documentation")["score"] == 3.0
    assert any("No README" in c for c in caps)


def test_committed_credentials_zero_security():
    metrics = {**GOOD_METRICS, "secrets": [{"type": "AWS access key id", "file": "a.py"}]}
    rows, _, caps = apply_rubric(GENEROUS, metrics, GOOD_GIT, {})
    assert next(r for r in rows if r["key"] == "security")["score"] == 0.0
    assert any("Credentials committed" in c for c in caps)


def test_two_commits_caps_git_hygiene():
    git = {"available": True, "commit_count": 2, "generic_ratio": 0.0}
    rows, _, caps = apply_rubric(GENEROUS, GOOD_METRICS, git, {})
    assert next(r for r in rows if r["key"] == "git_hygiene")["score"] == 3.0


def test_generic_commit_messages_cap_git_hygiene():
    git = {"available": True, "commit_count": 20, "generic_ratio": 0.9}
    rows, _, _ = apply_rubric(GENEROUS, GOOD_METRICS, git, {})
    assert next(r for r in rows if r["key"] == "git_hygiene")["score"] == 5.0


def test_heavy_lint_debt_caps_code_quality():
    lint = {"ruff": {"available": True, "per_kloc": 120}}
    rows, _, _ = apply_rubric(GENEROUS, GOOD_METRICS, GOOD_GIT, lint)
    assert next(r for r in rows if r["key"] == "code_quality")["score"] == 8.0


def test_a_terrible_repo_scores_low():
    metrics = {
        "tests": {"count": 0, "ratio": 0.0},
        "readme": {"exists": False, "chars": 0},
        "secrets": [{"type": "OpenAI API key", "file": "app.py"}],
        "possible_secrets": [],
        "dependencies": {"unpinned": ["flask", "requests", "numpy"]},
        "gitignore": {"exists": False},
        "committed_junk": ["node_modules committed to the repository"],
    }
    git = {"available": True, "commit_count": 1, "generic_ratio": 1.0}
    lint = {"ruff": {"available": True, "per_kloc": 95}}
    rows, total, caps = apply_rubric(GENEROUS, metrics, git, lint)
    scored = {r["key"]: r["score"] for r in rows}

    # Every category with hard evidence behind it is forced down, even though
    # the model claimed full marks on all seven.
    assert scored["testing"] == 2.0          # no tests
    assert scored["documentation"] == 3.0    # no README
    assert scored["security"] == 0.0         # leaked key
    assert scored["git_hygiene"] == 0.0      # 1 commit, no .gitignore, junk committed
    assert scored["code_quality"] == 8.0     # 95 lint issues per KLOC

    # structure and correctness have no static proxy, so they keep the model's
    # numbers -- which is why a generous model still lands at 48, not 0.
    assert total == 48.0
    assert len(caps) >= 5
    assert grade_for(total) == "F"


def test_an_empty_repo_earns_no_credit_for_having_nothing_to_leak():
    """Regression: octocat/Hello-World scored Security 10/10 on a live run,
    purely because a repo with no code has no credentials in it."""
    metrics = {
        **GOOD_METRICS,
        "total_loc": 1,
        "tests": {"count": 0, "ratio": 0.0},
        "readme": {"exists": True, "chars": 13, "has_setup": False},
    }
    rows, _, caps = apply_rubric(GENEROUS, metrics, GOOD_GIT, {})
    assert next(r for r in rows if r["key"] == "security")["score"] == 3.0
    assert any("too little to assess security" in c for c in caps)


def test_a_normal_sized_repo_is_not_hit_by_the_empty_repo_cap():
    rows, _, caps = apply_rubric(GENEROUS, GOOD_METRICS, GOOD_GIT, {})
    assert next(r for r in rows if r["key"] == "security")["score"] == 10.0
    assert not any("too little to assess" in c for c in caps)


def test_scores_are_clamped_to_the_category_maximum():
    inflated = [{"key": i["key"], "score": 999, "justification": ""} for i in RUBRIC]
    rows, total, _ = apply_rubric(inflated, GOOD_METRICS, GOOD_GIT, {})
    assert total == 100.0
    assert all(r["score"] <= r["max_score"] for r in rows)


def test_missing_categories_score_zero_rather_than_crashing():
    rows, total, _ = apply_rubric([], GOOD_METRICS, GOOD_GIT, {})
    assert total == 0.0
    assert len(rows) == len(RUBRIC)
