import json
import re
import tomllib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
UNPUBLISHED = {".venv", ".git", ".pytest_cache", ".ruff_cache", "__pycache__"}
FENCE = re.compile(r"^(```|~~~).*?^\1", re.DOTALL | re.MULTILINE)
INLINE_CODE = re.compile(r"`[^`\n]*`")
LINK = re.compile(r"\]\(([^)\s]+)[^)]*\)")
IMAGE = re.compile(r'<img src="([^"]+)"')
EXTERNAL = re.compile(r"^[a-z][a-z0-9+.-]*:|^#")
RELEASE_HEADING = re.compile(r"^## \[(\d[^\]]*)\]", re.MULTILINE)
PACKAGE_VERSION = re.compile(r'^name = "preview"\nversion = "([^"]+)"$', re.MULTILINE)


def markdown_files() -> Iterator[Path]:
    for path in sorted(ROOT.rglob("*.md")):
        if not UNPUBLISHED & set(path.relative_to(ROOT).parts):
            yield path


def prose(path: Path) -> str:
    return INLINE_CODE.sub("", FENCE.sub("", path.read_text()))


def targets(path: Path) -> list[str]:
    text = prose(path)
    return [target for target in LINK.findall(text) + IMAGE.findall(text) if not EXTERNAL.match(target)]


def relative_links() -> Iterator[tuple[Path, str]]:
    for path in markdown_files():
        for target in targets(path):
            yield path, target


def pyproject() -> dict[str, Any]:
    return tomllib.loads((ROOT / "pyproject.toml").read_text())


def project_version() -> str:
    return pyproject()["project"]["version"]


def link_id(value: object) -> str:
    return str(value.relative_to(ROOT)) if isinstance(value, Path) else str(value)


def test_markdown_links_are_found() -> None:
    assert any(path.name == "README.md" for path, _ in relative_links())


@pytest.mark.parametrize(("path", "target"), sorted(set(relative_links())), ids=link_id)
def test_markdown_link_resolves(path: Path, target: str) -> None:
    assert (path.parent / target.split("#", maxsplit=1)[0]).resolve().exists()


def test_plugin_version_matches_the_project() -> None:
    assert json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())["version"] == project_version()


def test_lock_version_matches_the_project() -> None:
    assert PACKAGE_VERSION.findall((ROOT / "uv.lock").read_text()) == [project_version()]


def test_latest_changelog_section_matches_the_project() -> None:
    assert RELEASE_HEADING.findall((ROOT / "CHANGELOG.md").read_text())[0] == project_version()


def test_bump_configuration_matches_the_project() -> None:
    assert pyproject()["tool"]["bumpversion"]["current_version"] == project_version()


def test_changelog_has_an_unreleased_section() -> None:
    assert "\n## [Unreleased]\n" in (ROOT / "CHANGELOG.md").read_text()


def test_license_is_apache() -> None:
    assert "Apache License" in (ROOT / "LICENSE").read_text()
    assert pyproject()["project"]["license"] == "Apache-2.0"
    assert json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())["license"] == "Apache-2.0"


def test_notice_names_the_project() -> None:
    assert "botifyex/preview" in (ROOT / "NOTICE").read_text()


def test_marketplace_lists_the_plugin_at_the_root() -> None:
    marketplace = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
    assert [(plugin["name"], plugin["source"]) for plugin in marketplace["plugins"]] == [("preview", "./")]


def workflow_paths(name: str) -> dict[str, Any]:
    return yaml.safe_load((ROOT / ".github" / "workflows" / name).read_text())[True]["push"]


def test_docs_workflow_covers_exactly_what_ci_ignores() -> None:
    assert workflow_paths("docs.yaml")["paths"] == workflow_paths("ci.yaml")["paths-ignore"]


def test_skill_files_always_run_the_whole_suite() -> None:
    assert not [path for path in workflow_paths("ci.yaml")["paths-ignore"] if path.startswith(("skills", "examples"))]
