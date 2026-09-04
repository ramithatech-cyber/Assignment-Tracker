"""Orchestrates one full analysis.

Deliberately free of FastAPI types: `run_analysis` takes plain values and
returns a plain result, so moving it onto a background worker later touches the
router only.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from app.config import settings
from app.services import collector, git_hygiene, github, inspector, linters, llm, scoring
from app.services.errors import AnalysisError

log = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    repo_owner: str
    repo_name: str
    default_branch: str
    commit_sha: str

    summary: str
    category_scores: list[dict[str, Any]]
    strengths: list[dict[str, Any]]
    improvements: list[dict[str, Any]]
    static_metrics: dict[str, Any]
    applied_caps: list[str]

    total_score: float
    grade: str
    llm_model: str
    tokens_used: int
    duration_ms: int
    files_reviewed: list[str] = field(default_factory=list)


_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _known_paths(inspection: inspector.Inspection) -> set[str]:
    return {entry.path for entry in inspection.files}


def _verify_citation(raw: Optional[str], known: set[str]) -> tuple[Optional[str], bool]:
    """Confirm a model-supplied `path.py:42` citation points at a real file."""
    if not raw:
        return None, False
    citation = raw.strip().lstrip("./").replace("\\", "/")
    path = citation.split(":", 1)[0]
    if path in known:
        return citation, True
    # Tolerate a leading repo-name segment, e.g. "my-project/app/main.py".
    tail = path.split("/", 1)[-1]
    if tail in known:
        return citation, True
    suffix_match = next((p for p in known if p.endswith("/" + path)), None)
    if suffix_match:
        return citation, True
    return citation, False


def _normalise_findings(
    items: Any, known: set[str], with_severity: bool
) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        citation, verified = _verify_citation(item.get("file"), known)
        entry = {
            "title": (item.get("title") or "").strip(),
            "detail": (item.get("detail") or "").strip(),
            "file": citation,
            "verified": verified,
        }
        if with_severity:
            severity = (item.get("severity") or "medium").lower()
            entry["severity"] = severity if severity in _SEVERITY_ORDER else "medium"
            entry["suggestion"] = (item.get("suggestion") or "").strip()
        if entry["title"] or entry["detail"]:
            cleaned.append(entry)
    if with_severity:
        cleaned.sort(key=lambda e: _SEVERITY_ORDER.get(e["severity"], 1))
    return cleaned


def run_analysis(
    repo_url: str,
    assignment_title: str,
    assignment_requirements: str,
) -> AnalysisResult:
    """Clone-free full analysis of a public GitHub repository.

    Raises AnalysisError with a student-facing message on any expected failure.
    """
    started = time.monotonic()

    ref = github.parse_repo_url(repo_url)
    metadata = github.fetch_metadata(ref)
    commits = github.fetch_commits(metadata.ref)
    git_stats = git_hygiene.analyse_commits(commits)
    commit_sha = commits[0]["sha"] if commits else ""

    fetched = github.download_repo(metadata.ref, metadata.default_branch)
    try:
        inspection = inspector.inspect_repo(fetched.root)
        if not inspection.files:
            raise AnalysisError(
                "No readable source files were found in this repository.",
                status_code=422,
            )

        lint_results = linters.run_all(fetched.root, inspection.languages)
        bundle, included = collector.build_bundle(
            inspection, metadata, lint_results, git_stats
        )
        log.info(
            "Analysing %s: %d files, %d LOC, bundle %d chars",
            metadata.ref.full_name, len(inspection.files), inspection.total_loc, len(bundle),
        )

        review, tokens = llm.review_repository(
            bundle, assignment_title, assignment_requirements
        )
    finally:
        fetched.cleanup()

    metrics = inspection.to_metrics()
    metrics["linters"] = lint_results
    metrics["git"] = git_stats
    metrics["fetch_method"] = fetched.method
    metrics["files_reviewed"] = included

    rows, total, caps = scoring.apply_rubric(
        review.get("categories") or [], metrics, git_stats, lint_results
    )
    known = _known_paths(inspection)

    return AnalysisResult(
        repo_owner=metadata.ref.owner,
        repo_name=metadata.ref.name,
        default_branch=metadata.default_branch,
        commit_sha=commit_sha,
        summary=(review.get("summary") or "").strip(),
        category_scores=rows,
        strengths=_normalise_findings(review.get("strengths"), known, with_severity=False),
        improvements=_normalise_findings(review.get("improvements"), known, with_severity=True),
        static_metrics=metrics,
        applied_caps=caps,
        total_score=total,
        grade=scoring.grade_for(total),
        llm_model=settings.openai_model,
        tokens_used=tokens,
        duration_ms=int((time.monotonic() - started) * 1000),
        files_reviewed=included,
    )
