"""Everything that talks to GitHub: URL validation, metadata, history, download.

Security note: the repo URL is attacker-controlled input that ends up driving a
network fetch (and, on machines that have git, a subprocess). The only safe
shape for that is a strict allowlist -- an exact host match plus a character
class for owner/repo -- so SSRF, `file://`, and argument injection are ruled out
before anything else runs.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import httpx

from app.config import settings
from app.services.errors import AnalysisError

# https://github.com/<owner>/<repo>  -- anything after that (tree/main, .git, a
# trailing slash) is tolerated and discarded, because students paste browser URLs.
_REPO_URL = re.compile(
    r"^https?://(?:www\.)?github\.com/"
    r"(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9\-]{0,38}))/"
    r"(?P<repo>[A-Za-z0-9._\-]{1,100}?)"
    r"(?:\.git)?(?:/.*)?$",
    re.IGNORECASE,
)


@dataclass
class RepoRef:
    owner: str
    name: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"

    @property
    def clone_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.name}.git"

    @property
    def canonical_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.name}"


@dataclass
class RepoMetadata:
    ref: RepoRef
    default_branch: str = "main"
    size_kb: int = 0
    stars: int = 0
    language: Optional[str] = None
    description: Optional[str] = None
    license_name: Optional[str] = None
    topics: list[str] = field(default_factory=list)
    pushed_at: Optional[str] = None
    created_at: Optional[str] = None
    has_issues: bool = False


def parse_repo_url(url: str) -> RepoRef:
    """Validate a user-supplied URL and reduce it to owner/name.

    Raises AnalysisError with a message that is safe to show the student.
    """
    candidate = (url or "").strip()
    if not candidate:
        raise AnalysisError("Please provide a GitHub repository URL.")

    match = _REPO_URL.match(candidate)
    if not match:
        raise AnalysisError(
            "That doesn't look like a public GitHub repository URL. "
            "Expected something like https://github.com/owner/repository"
        )

    owner = match.group("owner")
    name = match.group("repo").removesuffix(".git")

    if name in {".", ".."} or owner in {".", ".."}:
        raise AnalysisError("Invalid repository path.")

    return RepoRef(owner=owner, name=name)


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "assignment-tracker",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


def _raise_for_repo_status(response: httpx.Response, ref: RepoRef) -> None:
    if response.status_code == 404:
        raise AnalysisError(
            f"Repository {ref.full_name} was not found. "
            "Check the URL, and make sure the repository is public.",
            status_code=404,
        )
    if response.status_code in (401, 403):
        remaining = response.headers.get("x-ratelimit-remaining")
        if remaining == "0":
            raise AnalysisError(
                "GitHub's API rate limit has been reached. Set a GITHUB_TOKEN on "
                "the server, or try again in a few minutes.",
                status_code=429,
            )
        raise AnalysisError(
            f"GitHub denied access to {ref.full_name}. Private repositories "
            "cannot be analysed.",
            status_code=403,
        )
    if response.status_code >= 400:
        raise AnalysisError(
            f"GitHub returned {response.status_code} for {ref.full_name}.",
            status_code=502,
        )


def fetch_metadata(ref: RepoRef) -> RepoMetadata:
    url = f"{settings.github_api}/repos/{ref.owner}/{ref.name}"
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            response = client.get(url, headers=_headers())
    except httpx.HTTPError as exc:
        raise AnalysisError(f"Could not reach GitHub: {exc}", status_code=502) from exc

    _raise_for_repo_status(response, ref)
    data: dict[str, Any] = response.json()

    if data.get("private"):
        raise AnalysisError("Private repositories cannot be analysed.", status_code=403)

    size_kb = int(data.get("size") or 0)
    if size_kb > settings.max_repo_size_kb:
        raise AnalysisError(
            f"This repository is {size_kb // 1024} MB, which is over the "
            f"{settings.max_repo_size_kb // 1024} MB limit for analysis.",
            status_code=413,
        )

    license_info = data.get("license") or {}
    return RepoMetadata(
        # Use GitHub's canonical casing rather than whatever was pasted.
        ref=RepoRef(
            owner=(data.get("owner") or {}).get("login") or ref.owner,
            name=data.get("name") or ref.name,
        ),
        default_branch=data.get("default_branch") or "main",
        size_kb=size_kb,
        stars=int(data.get("stargazers_count") or 0),
        language=data.get("language"),
        description=data.get("description"),
        license_name=license_info.get("spdx_id") if license_info else None,
        topics=list(data.get("topics") or []),
        pushed_at=data.get("pushed_at"),
        created_at=data.get("created_at"),
        has_issues=bool(data.get("has_issues")),
    )


def fetch_commits(ref: RepoRef, limit: int = 100) -> list[dict[str, Any]]:
    """Recent commits. A tarball (and a shallow clone) has no history, so the
    API is the only source for git-hygiene signals."""
    url = f"{settings.github_api}/repos/{ref.owner}/{ref.name}/commits"
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            response = client.get(
                url, headers=_headers(), params={"per_page": min(limit, 100)}
            )
    except httpx.HTTPError:
        return []

    if response.status_code >= 400:
        return []

    commits = []
    for item in response.json():
        commit = item.get("commit") or {}
        author = commit.get("author") or {}
        commits.append(
            {
                "sha": item.get("sha", ""),
                "message": commit.get("message", ""),
                "author": author.get("name", ""),
                "date": author.get("date", ""),
            }
        )
    return commits


# ------------------------------------------------------------------ downloading


def _is_within(base: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _safe_extract(tar: tarfile.TarFile, dest: Path) -> None:
    """Extract, refusing anything that would escape `dest`.

    Written by hand rather than using `extractall(filter=...)`: that keyword
    only exists on newer patch releases and this has to work on 3.10.x.
    """
    dest_resolved = dest.resolve()
    for member in tar.getmembers():
        if member.issym() or member.islnk():
            continue  # symlinks are the classic tar-slip vector
        if not (member.isfile() or member.isdir()):
            continue
        if member.name.startswith("/") or ".." in Path(member.name).parts:
            continue
        target = dest_resolved / member.name
        if not _is_within(dest_resolved, target):
            continue
        tar.extract(member, dest_resolved)


def _download_tarball(ref: RepoRef, branch: str, dest: Path) -> Path:
    url = f"{settings.github_api}/repos/{ref.owner}/{ref.name}/tarball/{branch}"
    archive = dest / "repo.tar.gz"

    try:
        with httpx.Client(
            timeout=httpx.Timeout(settings.fetch_timeout, read=settings.fetch_timeout),
            follow_redirects=True,
        ) as client, client.stream("GET", url, headers=_headers()) as response:
            if response.status_code >= 400:
                raise AnalysisError(
                    f"Could not download {ref.full_name} (HTTP "
                    f"{response.status_code}).",
                    status_code=502,
                )
            written = 0
            cap = settings.max_repo_size_kb * 1024 * 3  # tar.gz + slack
            with archive.open("wb") as handle:
                for chunk in response.iter_bytes(chunk_size=1 << 16):
                    written += len(chunk)
                    if written > cap:
                        raise AnalysisError(
                            "Repository archive exceeded the size limit.",
                            status_code=413,
                        )
                    handle.write(chunk)
    except httpx.HTTPError as exc:
        raise AnalysisError(
            f"Download from GitHub failed: {exc}", status_code=502
        ) from exc

    extract_root = dest / "extracted"
    extract_root.mkdir(exist_ok=True)
    try:
        with tarfile.open(archive, "r:gz") as tar:
            _safe_extract(tar, extract_root)
    except tarfile.TarError as exc:
        raise AnalysisError(f"Repository archive was unreadable: {exc}", 502) from exc
    finally:
        archive.unlink(missing_ok=True)

    # GitHub wraps everything in a single `owner-repo-sha` directory.
    entries = [p for p in extract_root.iterdir() if p.is_dir()]
    if len(entries) == 1:
        return entries[0]
    if not entries and not any(extract_root.iterdir()):
        raise AnalysisError("The repository appears to be empty.", status_code=422)
    return extract_root


def _git_clone(ref: RepoRef, dest: Path) -> Optional[Path]:
    """Shallow clone, when a git binary happens to be available."""
    git = shutil.which("git")
    if not git:
        return None

    target = dest / "clone"
    env = {
        **os.environ,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ASKPASS": "",
        "GCM_INTERACTIVE": "never",
    }
    try:
        result = subprocess.run(
            [
                git, "clone", "--depth", "1", "--single-branch",
                "--no-tags", "--quiet", ref.clone_url, str(target),
            ],
            capture_output=True,
            timeout=settings.fetch_timeout,
            env=env,
            check=False,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    return target if result.returncode == 0 and target.exists() else None


@dataclass
class FetchedRepo:
    root: Path
    workdir: Path
    method: str

    def cleanup(self) -> None:
        shutil.rmtree(self.workdir, ignore_errors=True)


def download_repo(ref: RepoRef, branch: str = "main") -> FetchedRepo:
    """Materialise the repository on disk.

    The tarball endpoint is preferred: it needs no git binary, no subprocess,
    and is faster than a clone. git is only a fallback.

    Callers MUST call `.cleanup()` in a finally block.
    """
    workdir = Path(tempfile.mkdtemp(prefix="repo-analysis-"))
    try:
        root = _download_tarball(ref, branch, workdir)
        return FetchedRepo(root=root, workdir=workdir, method="tarball")
    except AnalysisError:
        cloned = _git_clone(ref, workdir)
        if cloned is not None:
            return FetchedRepo(root=cloned, workdir=workdir, method="git")
        shutil.rmtree(workdir, ignore_errors=True)
        raise
    except Exception:
        shutil.rmtree(workdir, ignore_errors=True)
        raise
