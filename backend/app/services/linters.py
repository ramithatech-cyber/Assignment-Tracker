"""Runs real static-analysis tools against the downloaded repository.

Every runner is best-effort: a missing binary, a crash, or a timeout degrades
that one tool to `available: false` and the rest of the pipeline carries on. A
student's submission must never fail because the grading server is missing npm.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Optional

from app.config import settings

# Explicit rule selection, applied with --isolated: every submission is measured
# against the same ruleset, so a student cannot improve their score by shipping a
# config that turns the linter off.
RUFF_SELECT = "E,W,F,I,B,C4,SIM,UP,ARG,RET,N,PIE"
RUFF_IGNORE = "E501,ARG002"


def _resolve(tool: str) -> Optional[list[str]]:
    """Find a console script, preferring the one in our own environment."""
    here = Path(sys.executable).parent
    for candidate in (
        here / f"{tool}.exe",
        here / tool,
        here / "Scripts" / f"{tool}.exe",
        here / "Scripts" / tool,
    ):
        if candidate.is_file():
            return [str(candidate)]
    found = shutil.which(tool)
    if found:
        return [found]
    return None


def _run(cmd: list[str], cwd: Path) -> Optional[subprocess.CompletedProcess]:
    try:
        return subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=settings.linter_timeout,
            check=False,
        )
    except (subprocess.SubprocessError, OSError):
        return None


# ------------------------------------------------------------------------ ruff
def run_ruff(root: Path, python_loc: int) -> dict[str, Any]:
    base = _resolve("ruff") or [sys.executable, "-m", "ruff"]
    result = _run(
        base
        + [
            "check", ".",
            "--output-format", "json",
            "--isolated",
            "--no-cache",
            "--select", RUFF_SELECT,
            "--ignore", RUFF_IGNORE,
            "--exit-zero",
        ],
        root,
    )
    if result is None or not result.stdout.strip():
        if result is not None and result.returncode == 0:
            return {"available": True, "issue_count": 0, "per_kloc": 0.0,
                    "top_rules": [], "samples": []}
        return {"available": False, "reason": "ruff could not be executed"}

    try:
        issues = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"available": False, "reason": "ruff output was not valid JSON"}

    counter: Counter[str] = Counter()
    samples: list[dict[str, Any]] = []
    for issue in issues:
        code = issue.get("code") or "?"
        counter[code] += 1
        if len(samples) < 25:
            location = issue.get("location") or {}
            samples.append(
                {
                    "file": issue.get("filename", "").replace(str(root), "").lstrip("\\/"),
                    "line": location.get("row"),
                    "code": code,
                    "message": issue.get("message", ""),
                }
            )

    per_kloc = round(len(issues) / (python_loc / 1000), 2) if python_loc >= 100 else 0.0
    return {
        "available": True,
        "issue_count": len(issues),
        "per_kloc": per_kloc,
        "top_rules": [
            {"code": code, "count": count} for code, count in counter.most_common(10)
        ],
        "samples": samples,
        "ruleset": RUFF_SELECT,
    }


# ----------------------------------------------------------------------- radon
def run_radon(root: Path) -> dict[str, Any]:
    base = _resolve("radon") or [sys.executable, "-m", "radon"]

    cc = _run(base + ["cc", "-j", "-s", "."], root)
    if cc is None or not cc.stdout.strip():
        return {"available": False, "reason": "radon could not be executed"}
    try:
        data = json.loads(cc.stdout)
    except json.JSONDecodeError:
        return {"available": False, "reason": "radon output was not valid JSON"}

    blocks: list[dict[str, Any]] = []
    for filename, entries in data.items():
        if not isinstance(entries, list):
            continue  # radon reports parse errors as a dict
        for entry in entries:
            blocks.append(
                {
                    "file": filename.lstrip("./\\"),
                    "name": entry.get("name"),
                    "line": entry.get("lineno"),
                    "complexity": entry.get("complexity", 0),
                    "rank": entry.get("rank", ""),
                }
            )

    if not blocks:
        return {"available": True, "blocks": 0, "avg_complexity": 0.0,
                "max_complexity": 0, "worst": [], "high_complexity_count": 0}

    complexities = [b["complexity"] for b in blocks]
    worst = sorted(blocks, key=lambda b: b["complexity"], reverse=True)[:10]

    result: dict[str, Any] = {
        "available": True,
        "blocks": len(blocks),
        "avg_complexity": round(sum(complexities) / len(complexities), 2),
        "max_complexity": max(complexities),
        # Rank C or worse == cyclomatic complexity above 10.
        "high_complexity_count": sum(1 for c in complexities if c > 10),
        "worst": worst,
    }

    mi = _run(base + ["mi", "-j", "."], root)
    if mi is not None and mi.stdout.strip():
        try:
            mi_data = json.loads(mi.stdout)
            scores = [
                v["mi"] for v in mi_data.values()
                if isinstance(v, dict) and isinstance(v.get("mi"), (int, float))
            ]
            if scores:
                result["maintainability_index"] = round(sum(scores) / len(scores), 1)
                result["worst_maintainability"] = round(min(scores), 1)
        except (json.JSONDecodeError, TypeError):
            pass

    return result


# ---------------------------------------------------------------------- eslint
ESLINT_CONFIGS = {
    ".eslintrc", ".eslintrc.json", ".eslintrc.js", ".eslintrc.cjs",
    ".eslintrc.yml", ".eslintrc.yaml", "eslint.config.js", "eslint.config.mjs",
    "eslint.config.cjs",
}


def run_eslint(root: Path, js_loc: int) -> dict[str, Any]:
    npx = shutil.which("npx")
    if not npx:
        return {"available": False, "reason": "Node.js/npx is not installed on the server"}
    if not any((root / name).exists() for name in ESLINT_CONFIGS):
        return {"available": False, "reason": "no ESLint config in the repository"}

    result = _run(
        [npx, "--no-install", "eslint", ".", "-f", "json", "--ext", ".js,.jsx,.ts,.tsx"],
        root,
    )
    if result is None or not result.stdout.strip():
        return {"available": False, "reason": "eslint could not be executed"}
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"available": False, "reason": "eslint output was not valid JSON"}

    errors = sum(f.get("errorCount", 0) for f in report)
    warnings = sum(f.get("warningCount", 0) for f in report)
    counter: Counter[str] = Counter()
    samples: list[dict[str, Any]] = []
    for entry in report:
        for message in entry.get("messages", []):
            rule = message.get("ruleId") or "syntax"
            counter[rule] += 1
            if len(samples) < 20:
                samples.append(
                    {
                        "file": entry.get("filePath", "").replace(str(root), "").lstrip("\\/"),
                        "line": message.get("line"),
                        "code": rule,
                        "message": message.get("message", ""),
                    }
                )

    total = errors + warnings
    return {
        "available": True,
        "issue_count": total,
        "errors": errors,
        "warnings": warnings,
        "per_kloc": round(total / (js_loc / 1000), 2) if js_loc >= 100 else 0.0,
        "top_rules": [{"code": r, "count": c} for r, c in counter.most_common(10)],
        "samples": samples,
    }


def run_all(root: Path, languages: dict[str, int]) -> dict[str, Any]:
    python_loc = languages.get("Python", 0)
    js_loc = languages.get("JavaScript", 0) + languages.get("TypeScript", 0)

    results: dict[str, Any] = {}
    if python_loc > 0:
        results["ruff"] = run_ruff(root, python_loc)
        results["radon"] = run_radon(root)
    if js_loc > 0:
        results["eslint"] = run_eslint(root, js_loc)
    return results
