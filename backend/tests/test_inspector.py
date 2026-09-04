"""The inspector against a synthetic repository with known contents."""

import textwrap
from pathlib import Path

import pytest

from app.services.inspector import inspect_repo


@pytest.fixture()
def sample_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "node_modules" / "left-pad").mkdir(parents=True)
    (root / ".github" / "workflows").mkdir(parents=True)

    (root / "README.md").write_text(
        "# Sample\n\n## Installation\n\n```bash\npip install -r requirements.txt\n```\n"
        "## Usage\n\nRun it.\n" + "Filler text to get past the 200 character floor. " * 5,
        encoding="utf-8",
    )
    (root / "requirements.txt").write_text("fastapi==0.115.6\nrequests\n", encoding="utf-8")
    (root / ".gitignore").write_text("__pycache__/\n.venv/\n", encoding="utf-8")
    (root / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    (root / "src" / "main.py").write_text(
        textwrap.dedent(
            '''
            """Module docstring."""


            def add(a, b):
                """Add two numbers."""
                return a + b


            def undocumented(x):
                return x * 2
            '''
        ).strip(),
        encoding="utf-8",
    )
    (root / "tests" / "test_main.py").write_text(
        "def test_add():\n    assert 1 + 1 == 2\n", encoding="utf-8"
    )
    (root / "node_modules" / "left-pad" / "index.js").write_text("//x\n", encoding="utf-8")
    return root


def test_counts_and_languages(sample_repo):
    result = inspect_repo(sample_repo)
    assert result.primary_language == "Python"
    assert result.total_loc > 0
    # node_modules must never reach the language stats or the LLM bundle.
    assert not any("node_modules" in f.path for f in result.files)


def test_detects_readme_tests_ci_and_gitignore(sample_repo):
    result = inspect_repo(sample_repo)
    assert result.readme["exists"] is True
    assert result.readme["has_setup"] is True
    assert result.tests["count"] == 1
    assert result.ci["exists"] is True
    assert result.gitignore["exists"] is True


def test_flags_committed_node_modules(sample_repo):
    result = inspect_repo(sample_repo)
    assert any("node_modules" in reason for reason in result.committed_junk)


def test_reports_unpinned_dependencies(sample_repo):
    result = inspect_repo(sample_repo)
    assert result.dependencies["unpinned"] == ["requests"]


def test_docstring_coverage(sample_repo):
    result = inspect_repo(sample_repo)
    # add() is documented, undocumented() is not.
    assert result.python_docs["definitions"] == 2
    assert result.python_docs["documented"] == 1


def test_detects_a_leaked_key_but_not_a_placeholder(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "settings.py").write_text(
        'AWS_KEY = "AKIAIOSFODNN7EXAMPLE"\n', encoding="utf-8"
    )
    (root / ".env.example").write_text(
        'OPENAI_API_KEY=sk-your-key-here-placeholder-value\n', encoding="utf-8"
    )
    (root / "config.py").write_text(
        'API_KEY = os.environ["API_KEY"]\nPASSWORD = "your-password-here"\n',
        encoding="utf-8",
    )

    result = inspect_repo(root)
    found = {s["file"] for s in result.secrets}
    assert "settings.py" in found
    assert ".env.example" not in found          # templates are exempt
    assert "config.py" not in found            # obvious placeholders are exempt
    assert all("AKIAIOSFODNN7EXAMPLE" not in s["preview"] for s in result.secrets)
