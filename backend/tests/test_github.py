"""URL validation is the security boundary: it decides what the server fetches."""

import pytest

from app.services.errors import AnalysisError
from app.services.github import parse_repo_url


@pytest.mark.parametrize(
    "url,owner,name",
    [
        ("https://github.com/psf/requests", "psf", "requests"),
        ("https://github.com/psf/requests.git", "psf", "requests"),
        ("https://github.com/psf/requests/", "psf", "requests"),
        ("http://github.com/psf/requests", "psf", "requests"),
        ("https://www.github.com/psf/requests", "psf", "requests"),
        ("https://github.com/psf/requests/tree/main/src", "psf", "requests"),
        ("  https://github.com/Some-Org/my_repo.v2  ", "Some-Org", "my_repo.v2"),
    ],
)
def test_accepts_real_github_urls(url, owner, name):
    ref = parse_repo_url(url)
    assert (ref.owner, ref.name) == (owner, name)


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not a url",
        "git@github.com:psf/requests.git",          # SSH
        "ssh://github.com/psf/requests",
        "file:///etc/passwd",                        # local file read
        "https://gitlab.com/psf/requests",           # other host
        "https://github.com.evil.example/psf/repo",  # lookalike host
        "https://127.0.0.1/psf/requests",            # SSRF at localhost
        "https://github.com/psf",                    # no repo
        "https://raw.githubusercontent.com/psf/requests/main/setup.py",
    ],
)
def test_rejects_everything_else(url):
    with pytest.raises(AnalysisError):
        parse_repo_url(url)


def test_clone_url_is_rebuilt_not_echoed():
    # The URL used downstream is constructed from the parsed parts, so nothing
    # the user typed can survive into a network call verbatim.
    ref = parse_repo_url("https://github.com/psf/requests/tree/main?x=1")
    assert ref.clone_url == "https://github.com/psf/requests.git"
