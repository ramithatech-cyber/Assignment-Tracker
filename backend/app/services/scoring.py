"""The rubric, and the evidence caps that keep the model honest.

The model supplies judgement; this module supplies the arithmetic and the hard
limits. A repository with no tests cannot be talked into a good Testing score no
matter how persuasive its README is -- which is what makes a grade defensible
when a student disputes it.
"""

from __future__ import annotations

from typing import Any

RUBRIC: list[dict[str, Any]] = [
    {
        "key": "code_quality",
        "label": "Code Quality & Readability",
        "max": 20,
        "guidance": "Naming, function length, duplication, dead code, consistent "
                    "style, error handling, magic numbers, linter findings per KLOC.",
    },
    {
        "key": "structure",
        "label": "Project Structure & Architecture",
        "max": 15,
        "guidance": "Sensible directory layout, separation of concerns, module "
                    "boundaries, no god-files, configuration kept out of code.",
    },
    {
        "key": "correctness",
        "label": "Correctness & Completeness",
        "max": 20,
        "guidance": "Does the code actually implement the assignment requirements? "
                    "Missing features, obvious bugs, unhandled edge cases, stubs.",
    },
    {
        "key": "documentation",
        "label": "Documentation",
        "max": 15,
        "guidance": "README quality, setup and run instructions, usage examples, "
                    "docstrings/comments where they earn their keep.",
    },
    {
        "key": "testing",
        "label": "Testing",
        "max": 10,
        "guidance": "Presence and quality of automated tests, coverage of the core "
                    "logic, meaningful assertions rather than smoke tests.",
    },
    {
        "key": "git_hygiene",
        "label": "Git Hygiene",
        "max": 10,
        "guidance": "Commit count and cadence, descriptive commit messages, a real "
                    ".gitignore, no build output or dependencies committed.",
    },
    {
        "key": "security",
        "label": "Security & Dependencies",
        "max": 10,
        "guidance": "No committed credentials, input validation, no obvious "
                    "injection paths, pinned and reasonable dependencies.",
    },
]

RUBRIC_BY_KEY = {item["key"]: item for item in RUBRIC}
TOTAL_POINTS = sum(item["max"] for item in RUBRIC)  # 100

# Below this, a repository is effectively empty and cannot be credited for the
# absence of problems.
MIN_LOC_TO_ASSESS = 50


def grade_for(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _clamp(value: float, maximum: float) -> float:
    return max(0.0, min(round(float(value), 1), float(maximum)))


def apply_rubric(
    llm_categories: list[dict[str, Any]],
    metrics: dict[str, Any],
    git_stats: dict[str, Any],
    lint_results: dict[str, Any],
) -> tuple[list[dict[str, Any]], float, list[str]]:
    """Merge the model's per-category scores with the hard evidence.

    Returns (category rows, total out of 100, list of caps that fired).
    """
    by_key = {c.get("key"): c for c in llm_categories if isinstance(c, dict)}
    caps: list[str] = []

    scores: dict[str, float] = {}
    justifications: dict[str, str] = {}
    for item in RUBRIC:
        raw = by_key.get(item["key"]) or {}
        scores[item["key"]] = _clamp(raw.get("score", 0), item["max"])
        justifications[item["key"]] = (raw.get("justification") or "").strip()

    def cap(key: str, ceiling: float, reason: str) -> None:
        if scores[key] > ceiling:
            scores[key] = float(ceiling)
            caps.append(reason)

    def penalise(key: str, amount: float, reason: str) -> None:
        if scores[key] > 0:
            scores[key] = max(0.0, scores[key] - amount)
            caps.append(reason)

    # --- Testing ------------------------------------------------------------
    tests = metrics.get("tests") or {}
    if tests.get("count", 0) == 0:
        cap("testing", 2, "No test files found anywhere in the repository (Testing capped at 2/10).")
    elif tests.get("ratio", 0) < 0.05:
        cap("testing", 6, "Test code is under 5% of source code (Testing capped at 6/10).")

    # --- Documentation ------------------------------------------------------
    readme = metrics.get("readme") or {}
    if not readme.get("exists"):
        cap("documentation", 3, "No README file (Documentation capped at 3/15).")
    elif readme.get("chars", 0) < 200:
        cap("documentation", 4, "README is under 200 characters (Documentation capped at 4/15).")
    elif not readme.get("has_setup"):
        cap("documentation", 11, "README has no setup or installation instructions (Documentation capped at 11/15).")

    # --- Security -----------------------------------------------------------
    secrets = metrics.get("secrets") or []
    # Key-shaped material under tests/ or fixtures/ is reported to the student
    # but never scored as a leak -- TLS test certificates are not a breach.
    suspects = [s for s in (metrics.get("possible_secrets") or []) if not s.get("fixture")]
    if secrets:
        kinds = ", ".join(sorted({s.get("type", "credential") for s in secrets})[:3])
        cap("security", 0, f"Credentials committed to the repository ({kinds}) — Security scored 0/10.")
    elif suspects:
        cap("security", 6, "Hardcoded secret-looking values found in source (Security capped at 6/10).")

    unpinned = (metrics.get("dependencies") or {}).get("unpinned") or []
    if len(unpinned) >= 3:
        penalise("security", 1, f"{len(unpinned)} dependencies are unpinned in requirements.txt (-1).")

    # Security is the one category that rewards absence: a repository with no
    # code has nothing to leak and would otherwise collect full marks for it.
    total_loc = metrics.get("total_loc", 0)
    if total_loc < MIN_LOC_TO_ASSESS:
        cap(
            "security",
            3,
            f"Only {total_loc} lines of code — too little to assess security "
            "meaningfully (Security capped at 3/10).",
        )

    # --- Git hygiene --------------------------------------------------------
    if git_stats.get("available"):
        commit_count = git_stats.get("commit_count", 0)
        if commit_count < 3:
            cap("git_hygiene", 3, f"Only {commit_count} commit(s) in the repository (Git Hygiene capped at 3/10).")
        elif git_stats.get("generic_ratio", 0) > 0.6:
            cap("git_hygiene", 5, "Most commit messages are generic ('update', 'fix', ...) — Git Hygiene capped at 5/10.")

    if not (metrics.get("gitignore") or {}).get("exists"):
        penalise("git_hygiene", 2, "No .gitignore file (-2).")
    junk = metrics.get("committed_junk") or []
    if junk:
        penalise("git_hygiene", 3, f"Build artefacts or dependencies committed: {junk[0]} (-3).")

    # --- Code quality -------------------------------------------------------
    for tool in ("ruff", "eslint"):
        result = lint_results.get(tool) or {}
        if not result.get("available"):
            continue
        per_kloc = result.get("per_kloc", 0)
        if per_kloc > 80:
            cap("code_quality", 8, f"{tool} reports {per_kloc} issues per 1000 lines (Code Quality capped at 8/20).")
        elif per_kloc > 40:
            cap("code_quality", 12, f"{tool} reports {per_kloc} issues per 1000 lines (Code Quality capped at 12/20).")

    radon = lint_results.get("radon") or {}
    if radon.get("available") and radon.get("max_complexity", 0) > 25:
        cap("code_quality", 14, f"A function has cyclomatic complexity {radon['max_complexity']} (Code Quality capped at 14/20).")

    rows = [
        {
            "key": item["key"],
            "label": item["label"],
            "score": round(scores[item["key"]], 1),
            "max_score": float(item["max"]),
            "justification": justifications[item["key"]] or "No justification returned.",
        }
        for item in RUBRIC
    ]
    total = round(sum(row["score"] for row in rows), 1)
    return rows, total, caps


def rubric_prompt_block() -> str:
    lines = []
    for item in RUBRIC:
        lines.append(f"- `{item['key']}` — {item['label']} (0–{item['max']} points): {item['guidance']}")
    return "\n".join(lines)
