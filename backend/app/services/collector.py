"""Turns an inspected repository into a single markdown bundle for the model.

The whole repo will not fit in a context window, so this picks the files a human
reviewer would actually open: the README, the manifests, the entrypoints, and
then the largest / most central source files, each truncated.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import settings
from app.services.inspector import FileEntry, Inspection

MAX_LINES_PER_FILE = 300

ENTRYPOINT_NAMES = {
    "main.py", "app.py", "__main__.py", "manage.py", "wsgi.py", "asgi.py",
    "server.py", "run.py", "cli.py", "index.js", "index.ts", "main.js",
    "main.ts", "main.tsx", "app.tsx", "app.jsx", "server.js", "index.jsx",
    "main.go", "main.rs", "main.java", "program.cs",
}

ALWAYS_INCLUDE = {
    "readme.md", "requirements.txt", "package.json", "pyproject.toml",
    "dockerfile", "docker-compose.yml", ".gitignore", "go.mod", "cargo.toml",
}

GENERATED_HINTS = ("migrations/", "generated/", ".min.", "vendor/", "locale/")


def _priority(entry: FileEntry) -> float:
    """Higher is more interesting to a reviewer."""
    name = Path(entry.path).name.lower()
    depth = entry.path.count("/")
    score = float(entry.loc)

    if name in ALWAYS_INCLUDE:
        return 10_000.0
    if name in ENTRYPOINT_NAMES:
        score += 3_000
    if entry.language in {"Python", "TypeScript", "JavaScript"}:
        score += 500
    elif entry.language is None:
        score -= 400
    if entry.is_test:
        score += 250  # a couple of tests are worth seeing, but not all of them
    if any(hint in entry.path.lower() for hint in GENERATED_HINTS):
        score -= 2_000
    if entry.loc < 5:
        score -= 500
    score -= depth * 60
    return score


def _read_snippet(root: Path, entry: FileEntry) -> str:
    try:
        with (root / entry.path).open("r", encoding="utf-8", errors="replace") as handle:
            lines = handle.read(400_000).splitlines()
    except OSError:
        return ""
    truncated = len(lines) > MAX_LINES_PER_FILE
    body = "\n".join(lines[:MAX_LINES_PER_FILE])
    if truncated:
        body += f"\n... [{len(lines) - MAX_LINES_PER_FILE} more lines truncated]"
    return body


def _fence(path: str) -> str:
    return {
        ".py": "python", ".ts": "ts", ".tsx": "tsx", ".js": "js", ".jsx": "jsx",
        ".json": "json", ".md": "markdown", ".yml": "yaml", ".yaml": "yaml",
        ".sh": "bash", ".sql": "sql", ".html": "html", ".css": "css",
        ".toml": "toml", ".java": "java", ".go": "go", ".rs": "rust",
    }.get(Path(path).suffix.lower(), "")


def build_bundle(
    inspection: Inspection,
    metadata: Any,
    lint_results: dict[str, Any],
    git_stats: dict[str, Any],
) -> tuple[str, list[str]]:
    """Returns (markdown bundle, list of file paths actually included)."""
    budget = settings.llm_context_chars
    parts: list[str] = []

    parts.append(
        "# Repository under review\n\n"
        f"- Repository: `{metadata.ref.full_name}`\n"
        f"- Description: {metadata.description or '(none)'}\n"
        f"- Default branch: `{metadata.default_branch}`\n"
        f"- Size: {metadata.size_kb} KB · Stars: {metadata.stars}\n"
        f"- GitHub primary language: {metadata.language or 'unknown'}\n"
        f"- License: {metadata.license_name or 'none declared'}\n"
    )

    langs = ", ".join(f"{k} ({v} LOC)" for k, v in list(inspection.languages.items())[:8])
    parts.append(
        "## Measured facts (from static analysis — treat these as ground truth)\n\n"
        f"- Files scanned: {len(inspection.files)} of {inspection.total_files}\n"
        f"- Total lines of code: {inspection.total_loc}\n"
        f"- Languages: {langs or 'none detected'}\n"
        f"- README: {'present, ' + str(inspection.readme.get('chars', 0)) + ' chars' if inspection.readme.get('exists') else 'MISSING'}"
        f"{', has setup instructions' if inspection.readme.get('has_setup') else ', no setup instructions'}\n"
        f"- Test files: {inspection.tests.get('count', 0)} "
        f"(test LOC {inspection.tests.get('test_loc', 0)} vs source LOC {inspection.tests.get('source_loc', 0)}, "
        f"ratio {inspection.tests.get('ratio', 0)})\n"
        f"- CI configuration: {'yes — ' + ', '.join(inspection.ci.get('files', [])) if inspection.ci.get('exists') else 'none'}\n"
        f"- .gitignore: {'present, ' + str(inspection.gitignore.get('rules', 0)) + ' rules' if inspection.gitignore.get('exists') else 'MISSING'}\n"
        f"- Committed junk: {'; '.join(inspection.committed_junk) or 'none detected'}\n"
        f"- Leaked credentials: {json.dumps(inspection.secrets[:5]) if inspection.secrets else 'none detected'}\n"
        f"- Possible hardcoded secrets: {json.dumps(inspection.possible_secrets[:5]) if inspection.possible_secrets else 'none detected'}\n"
        f"- Dependency files: {', '.join(inspection.dependency_files) or 'none'}\n"
        f"- Unpinned Python dependencies: {', '.join((inspection.dependencies.get('unpinned') or [])[:10]) or 'none'}\n"
        f"- Python docstring coverage: {json.dumps(inspection.python_docs) if inspection.python_docs else 'n/a'}\n"
    )

    if lint_results:
        parts.append("## Linter output\n\n```json\n" + json.dumps(lint_results, indent=2)[:12_000] + "\n```\n")

    if git_stats.get("available"):
        parts.append("## Commit history\n\n```json\n" + json.dumps(git_stats, indent=2)[:6_000] + "\n```\n")
    else:
        parts.append("## Commit history\n\nNot available.\n")

    parts.append("## File tree\n\n```\n" + inspection.file_tree[:15_000] + "\n```\n")

    header_chars = sum(len(p) for p in parts)
    remaining = max(budget - header_chars, 20_000)

    ranked = sorted(inspection.files, key=_priority, reverse=True)
    included: list[str] = []
    file_parts: list[str] = ["## Source files\n"]

    for entry in ranked:
        if remaining <= 0 or len(included) >= 40:
            break
        snippet = _read_snippet(inspection.root, entry)
        if not snippet.strip():
            continue
        block = (
            f"\n### `{entry.path}` ({entry.loc} lines)\n\n"
            f"```{_fence(entry.path)}\n{snippet}\n```\n"
        )
        if len(block) > remaining and included:
            continue
        file_parts.append(block)
        included.append(entry.path)
        remaining -= len(block)

    skipped = len(inspection.files) - len(included)
    if skipped > 0:
        file_parts.append(
            f"\n_({skipped} further files were not included in this excerpt; "
            "judge only what you can see, and say so if coverage is partial.)_\n"
        )

    return "\n".join(parts + file_parts), included
