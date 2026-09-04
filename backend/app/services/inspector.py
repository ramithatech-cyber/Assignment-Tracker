"""Walks a downloaded repository and produces deterministic facts about it.

Nothing in here asks an LLM anything. Everything it returns is measurable, and
these measurements are what the scoring caps key off -- so two runs over the
same commit produce the same numbers.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from app.config import settings

SKIP_DIRS = {
    ".git", ".github_cache", "node_modules", ".venv", "venv", "env", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", "dist", "build", "out",
    ".next", ".nuxt", ".svelte-kit", "target", "vendor", "coverage", "htmlcov",
    ".idea", ".vscode", ".gradle", "Pods", "bower_components", ".terraform",
    ".parcel-cache", ".cache", "site-packages", ".eggs",
}

BINARY_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".svg", ".pdf",
    ".zip", ".gz", ".tar", ".rar", ".7z", ".exe", ".dll", ".so", ".dylib",
    ".pyc", ".pyo", ".class", ".jar", ".war", ".mp3", ".mp4", ".mov", ".avi",
    ".woff", ".woff2", ".ttf", ".eot", ".otf", ".db", ".sqlite", ".sqlite3",
    ".pkl", ".joblib", ".h5", ".onnx", ".bin", ".dat", ".lock", ".psd",
}

LANGUAGES = {
    ".py": "Python", ".ipynb": "Jupyter", ".js": "JavaScript", ".jsx": "JavaScript",
    ".mjs": "JavaScript", ".cjs": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript", ".java": "Java", ".kt": "Kotlin", ".go": "Go",
    ".rs": "Rust", ".rb": "Ruby", ".php": "PHP", ".cs": "C#", ".c": "C",
    ".h": "C", ".cpp": "C++", ".cc": "C++", ".hpp": "C++", ".swift": "Swift",
    ".dart": "Dart", ".scala": "Scala", ".r": "R", ".m": "Objective-C",
    ".sql": "SQL", ".sh": "Shell", ".ps1": "PowerShell", ".html": "HTML",
    ".css": "CSS", ".scss": "SCSS", ".vue": "Vue", ".svelte": "Svelte",
}

DOC_EXT = {".md", ".rst", ".txt", ".adoc"}

DEPENDENCY_FILES = {
    "requirements.txt", "requirements-dev.txt", "pyproject.toml", "Pipfile",
    "setup.py", "setup.cfg", "environment.yml", "package.json", "go.mod",
    "Cargo.toml", "pom.xml", "build.gradle", "Gemfile", "composer.json",
}

CONFIG_FILES = {
    "dockerfile", "docker-compose.yml", "docker-compose.yaml", "makefile",
    ".editorconfig", ".prettierrc", ".eslintrc", ".eslintrc.json", ".eslintrc.js",
    "eslint.config.js", "eslint.config.mjs", "tsconfig.json", "vite.config.ts",
    "vite.config.js", ".pre-commit-config.yaml", "ruff.toml", ".flake8",
    "tox.ini", "pytest.ini", "jest.config.js", "vitest.config.ts", "netlify.toml",
    "vercel.json", "procfile", "railway.json", "render.yaml",
}

JUNK_PATTERNS = [
    ("node_modules/", "node_modules committed to the repository"),
    ("__pycache__/", "__pycache__ committed to the repository"),
    (".venv/", "virtualenv committed to the repository"),
    ("venv/", "virtualenv committed to the repository"),
    (".DS_Store", "macOS .DS_Store files committed"),
    ("Thumbs.db", "Windows Thumbs.db committed"),
    (".idea/", "IDE settings committed"),
    ("dist/", "build output committed"),
    ("build/", "build output committed"),
    (".env", "a .env file is committed to the repository"),
]

# High-confidence: these shapes are what they are. Any hit is treated as a real
# leaked credential and zeroes the security category.
HARD_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("AWS access key id", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("OpenAI API key", re.compile(r"sk-(?:proj-)?[A-Za-z0-9_\-]{20,}")),
    ("GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("Google API key", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("Slack token", re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}")),
    ("Stripe secret key", re.compile(r"sk_live_[0-9a-zA-Z]{24,}")),
    ("Private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    (
        "Database URL with inline password",
        re.compile(r"(?:postgres(?:ql)?|mysql|mongodb)(?:\+\w+)?://[^:\s/]+:[^@\s]{4,}@"),
    ),
]

# Lower confidence: reported to the student, but never used to zero a score.
SOFT_SECRET_PATTERN = re.compile(
    r"""(?ix)
    \b(api[_-]?key|secret[_-]?key|secret|password|passwd|access[_-]?token|auth[_-]?token)
    \s*[:=]\s*
    ["'`]([^"'`\n]{8,})["'`]
    """
)

PLACEHOLDER_HINT = re.compile(
    r"(?i)(your|xxx|placeholder|change[_-]?me|example|dummy|sample|todo|none|null"
    r"|\$\{|\{\{|<[a-z]|os\.environ|process\.env|getenv|settings\.|config\.)"
)

TEST_DIR_NAMES = {"test", "tests", "__tests__", "spec", "e2e", "testing"}
TEST_FILE = re.compile(r"(?i)(^test_|_test\.|\.test\.|\.spec\.|^tests?\.py$|_spec\.)")

# Directories where key-shaped material is expected: TLS fixtures for a test
# suite are not a leaked production credential, and grading them as one would be
# both wrong and infuriating.
FIXTURE_DIR_NAMES = TEST_DIR_NAMES | {
    "fixtures", "fixture", "testdata", "test_data", "mocks", "__mocks__",
    "certs", "certificates", "examples", "example", "samples", "sample",
}


@dataclass
class FileEntry:
    path: str
    ext: str
    size: int
    loc: int
    language: Optional[str]
    is_test: bool


@dataclass
class Inspection:
    root: Path
    files: list[FileEntry] = field(default_factory=list)
    truncated: bool = False

    total_files: int = 0
    total_loc: int = 0
    languages: dict[str, int] = field(default_factory=dict)
    primary_language: Optional[str] = None

    file_tree: str = ""
    readme: dict[str, Any] = field(default_factory=dict)
    tests: dict[str, Any] = field(default_factory=dict)
    ci: dict[str, Any] = field(default_factory=dict)
    gitignore: dict[str, Any] = field(default_factory=dict)
    docs: list[str] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)
    dependency_files: list[str] = field(default_factory=list)
    dependencies: dict[str, Any] = field(default_factory=dict)
    committed_junk: list[str] = field(default_factory=list)
    secrets: list[dict[str, Any]] = field(default_factory=list)
    possible_secrets: list[dict[str, Any]] = field(default_factory=list)
    python_docs: dict[str, Any] = field(default_factory=dict)

    def to_metrics(self) -> dict[str, Any]:
        """The JSON blob persisted on the report and shown in the UI."""
        return {
            "total_files": self.total_files,
            "analysed_files": len(self.files),
            "truncated": self.truncated,
            "total_loc": self.total_loc,
            "languages": self.languages,
            "primary_language": self.primary_language,
            "readme": self.readme,
            "tests": self.tests,
            "ci": self.ci,
            "gitignore": self.gitignore,
            "docs": self.docs,
            "config_files": self.config_files,
            "dependency_files": self.dependency_files,
            "dependencies": self.dependencies,
            "committed_junk": self.committed_junk,
            "secrets": self.secrets,
            "possible_secrets": self.possible_secrets,
            "python_docstrings": self.python_docs,
        }


def _read_text(path: Path, limit: int) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return handle.read(limit)
    except OSError:
        return ""


def _is_test_path(rel: str) -> bool:
    parts = rel.replace("\\", "/").split("/")
    if any(p.lower() in TEST_DIR_NAMES for p in parts[:-1]):
        return True
    return bool(TEST_FILE.search(parts[-1]))


def _is_fixture_path(rel: str) -> bool:
    parts = rel.replace("\\", "/").split("/")
    return any(p.lower() in FIXTURE_DIR_NAMES for p in parts[:-1])


def _render_tree(root: Path, max_entries: int = 400, max_depth: int = 4) -> str:
    lines: list[str] = []

    def walk(directory: Path, prefix: str, depth: int) -> None:
        if depth > max_depth or len(lines) >= max_entries:
            return
        try:
            entries = sorted(
                directory.iterdir(), key=lambda p: (p.is_file(), p.name.lower())
            )
        except OSError:
            return
        entries = [e for e in entries if not (e.is_dir() and e.name in SKIP_DIRS)]
        for index, entry in enumerate(entries):
            if len(lines) >= max_entries:
                lines.append(f"{prefix}... (truncated)")
                return
            last = index == len(entries) - 1
            lines.append(f"{prefix}{'└── ' if last else '├── '}{entry.name}")
            if entry.is_dir():
                walk(entry, prefix + ("    " if last else "│   "), depth + 1)

    walk(root, "", 1)
    return "\n".join(lines)


def _analyse_readme(root: Path) -> dict[str, Any]:
    for name in ("README.md", "README.rst", "README.txt", "README", "readme.md"):
        candidate = root / name
        if candidate.is_file():
            text = _read_text(candidate, 200_000)
            headings = re.findall(r"^#{1,6}\s+(.+)$", text, re.MULTILINE)
            lowered = text.lower()
            return {
                "exists": True,
                "path": name,
                "chars": len(text),
                "lines": text.count("\n") + 1,
                "headings": headings[:25],
                "has_setup": any(
                    k in lowered
                    for k in ("install", "setup", "getting started", "prerequisit")
                ),
                "has_usage": any(
                    k in lowered for k in ("usage", "how to run", "run the", "example")
                ),
                "has_code_blocks": "```" in text,
                "excerpt": text[:4000],
            }
    return {"exists": False, "chars": 0, "headings": [], "excerpt": ""}


def _analyse_python_docstrings(files: list[FileEntry], root: Path) -> dict[str, Any]:
    definitions = 0
    documented = 0
    module_docs = 0
    modules = 0
    for entry in files:
        if entry.ext != ".py" or entry.is_test:
            continue
        source = _read_text(root / entry.path, 400_000)
        if not source.strip():
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        modules += 1
        if ast.get_docstring(tree):
            module_docs += 1
        for node in ast.walk(tree):
            if isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                if node.name.startswith("_") and not node.name.startswith("__"):
                    continue  # private helpers don't need public docs
                definitions += 1
                if ast.get_docstring(node):
                    documented += 1
    if definitions == 0 and modules == 0:
        return {}
    return {
        "definitions": definitions,
        "documented": documented,
        "ratio": round(documented / definitions, 3) if definitions else 0.0,
        "modules": modules,
        "modules_with_docstring": module_docs,
    }


def _parse_dependencies(root: Path, names: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {"python": [], "node": {}, "unpinned": [], "count": 0}

    req = root / "requirements.txt"
    if req.is_file():
        for raw in _read_text(req, 100_000).splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line or line.startswith("-"):
                continue
            result["python"].append(line)
            if not re.search(r"[=<>~!]=|@", line):
                result["unpinned"].append(line)

    pkg = root / "package.json"
    if pkg.is_file():
        import json

        try:
            data = json.loads(_read_text(pkg, 200_000) or "{}")
        except json.JSONDecodeError:
            data = {}
        deps = {**(data.get("dependencies") or {}), **(data.get("devDependencies") or {})}
        result["node"] = deps
        result["node_scripts"] = list((data.get("scripts") or {}).keys())

    result["count"] = len(result["python"]) + len(result["node"])
    result["files"] = names
    return result


def _scan_secrets(entry: FileEntry, text: str) -> tuple[list[dict], list[dict]]:
    hard: list[dict[str, Any]] = []
    soft: list[dict[str, Any]] = []
    name = Path(entry.path).name.lower()

    # Templates are supposed to contain key-shaped placeholders.
    is_template = (
        ".example" in name or ".sample" in name or name.endswith(".template")
        or name in {"env.example", ".env.example", ".env.sample", ".env.template"}
    )
    # Test fixtures are reported, but never treated as a leaked credential.
    is_fixture = _is_fixture_path(entry.path)

    for line_no, line in enumerate(text.splitlines()[:5000], start=1):
        if len(line) > 2000:
            continue
        for label, pattern in HARD_SECRET_PATTERNS:
            match = pattern.search(line)
            if match and not is_template:
                finding = {
                    "type": label,
                    "file": entry.path,
                    "line": line_no,
                    "preview": _redact(match.group(0)),
                }
                if is_fixture:
                    finding["fixture"] = True
                    soft.append(finding)
                else:
                    hard.append(finding)
                break
        soft_match = SOFT_SECRET_PATTERN.search(line)
        if soft_match and not is_template:
            value = soft_match.group(2)
            if not PLACEHOLDER_HINT.search(value) and not PLACEHOLDER_HINT.search(line):
                soft.append(
                    {
                        "type": f"hardcoded {soft_match.group(1).lower()}",
                        "file": entry.path,
                        "line": line_no,
                        "preview": _redact(value),
                        "fixture": is_fixture,
                    }
                )
    return hard, soft


def _redact(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * 8}{value[-2:]}"


def inspect_repo(root: Path) -> Inspection:
    """Walk `root` and gather every deterministic signal we can."""
    inspection = Inspection(root=root)
    languages: dict[str, int] = {}
    dependency_names: list[str] = []
    junk_reasons: set[str] = set()

    for path in sorted(root.rglob("*")):
        rel_parts = path.relative_to(root).parts

        if any(part in SKIP_DIRS for part in rel_parts):
            # Still worth noting that the junk was committed in the first place.
            for marker, reason in JUNK_PATTERNS:
                if marker.rstrip("/") in rel_parts:
                    junk_reasons.add(reason)
            continue
        if not path.is_file():
            continue

        rel = "/".join(rel_parts)
        inspection.total_files += 1

        name_lower = path.name.lower()
        for marker, reason in JUNK_PATTERNS:
            if marker.endswith("/"):
                continue
            if name_lower == marker.lower() or rel.endswith(marker):
                junk_reasons.add(reason)

        if name_lower in {n.lower() for n in DEPENDENCY_FILES}:
            dependency_names.append(rel)
        if name_lower in CONFIG_FILES:
            inspection.config_files.append(rel)

        ext = path.suffix.lower()
        if ext in DOC_EXT and rel.lower() != "readme.md":
            inspection.docs.append(rel)

        try:
            size = path.stat().st_size
        except OSError:
            continue

        if ext in BINARY_EXT or size > settings.max_file_bytes:
            continue
        if len(inspection.files) >= settings.max_files:
            inspection.truncated = True
            continue

        text = _read_text(path, settings.max_file_bytes)
        if "\x00" in text[:2048]:
            continue  # binary that slipped past the extension list

        loc = sum(1 for line in text.splitlines() if line.strip())
        language = LANGUAGES.get(ext)
        entry = FileEntry(
            path=rel,
            ext=ext,
            size=size,
            loc=loc,
            language=language,
            is_test=_is_test_path(rel),
        )
        inspection.files.append(entry)

        if language:
            languages[language] = languages.get(language, 0) + loc
            inspection.total_loc += loc

        hard, soft = _scan_secrets(entry, text)
        inspection.secrets.extend(hard)
        inspection.possible_secrets.extend(soft)

    inspection.languages = dict(
        sorted(languages.items(), key=lambda kv: kv[1], reverse=True)
    )
    inspection.primary_language = next(iter(inspection.languages), None)
    inspection.file_tree = _render_tree(root)
    inspection.readme = _analyse_readme(root)
    inspection.committed_junk = sorted(junk_reasons)
    inspection.dependency_files = dependency_names
    inspection.dependencies = _parse_dependencies(root, dependency_names)
    inspection.python_docs = _analyse_python_docstrings(inspection.files, root)

    # Only actual code counts as a test. A directory of .pem fixtures under
    # tests/ is not 26 extra tests.
    test_files = [f for f in inspection.files if f.is_test and f.language]
    source_loc = sum(f.loc for f in inspection.files if f.language and not f.is_test)
    test_loc = sum(f.loc for f in test_files)
    inspection.tests = {
        "count": len(test_files),
        "files": [f.path for f in test_files][:40],
        "test_loc": test_loc,
        "source_loc": source_loc,
        "ratio": round(test_loc / source_loc, 3) if source_loc else 0.0,
    }

    workflows = [
        f.path for f in inspection.files if f.path.startswith(".github/workflows/")
    ]
    ci_others = [
        f.path
        for f in inspection.files
        if Path(f.path).name
        in {".gitlab-ci.yml", ".travis.yml", "azure-pipelines.yml", "Jenkinsfile", ".circleci/config.yml"}
    ]
    inspection.ci = {
        "exists": bool(workflows or ci_others),
        "files": (workflows + ci_others)[:10],
    }

    gitignore = root / ".gitignore"
    if gitignore.is_file():
        content = _read_text(gitignore, 50_000)
        rules = [ln for ln in content.splitlines() if ln.strip() and not ln.startswith("#")]
        inspection.gitignore = {"exists": True, "rules": len(rules), "excerpt": content[:1500]}
    else:
        inspection.gitignore = {"exists": False, "rules": 0, "excerpt": ""}

    # Cap the noisiest lists so a bad repo can't blow up the payload.
    inspection.secrets = inspection.secrets[:25]
    inspection.possible_secrets = inspection.possible_secrets[:25]
    inspection.docs = inspection.docs[:30]
    inspection.config_files = inspection.config_files[:30]

    return inspection
