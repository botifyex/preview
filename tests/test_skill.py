import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from support import run_script

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "preview"
SKILL_TEXT = (SKILL / "SKILL.md").read_text()
README_TEXT = (ROOT / "README.md").read_text()
SCRIPTS = ["resolve_range.py", "capture.py", "check_report.py"]
LINE_LIMIT = 200
DESCRIPTION_LIMIT = 1536


def frontmatter() -> dict[str, str]:
    block = SKILL_TEXT.split("---\n")[1]
    return dict(line.split(": ", 1) for line in block.splitlines())


def test_frontmatter_follows_the_conventions() -> None:
    fields = frontmatter()
    assert fields["name"] == "preview"
    assert {"description", "when_to_use", "argument-hint"} <= set(fields)
    assert len(fields["description"]) + len(fields["when_to_use"]) < DESCRIPTION_LIMIT


def test_skill_stays_short() -> None:
    assert len(SKILL_TEXT.splitlines()) <= LINE_LIMIT


@pytest.mark.parametrize("path", re.findall(r"\]\((references/[^)]+)\)", SKILL_TEXT))
def test_skill_links_exist(path: str) -> None:
    assert (SKILL / path).is_file()


@pytest.mark.parametrize("path", re.findall(r"\]\(((?:skills|docs)/[^)]+)\)", README_TEXT))
def test_readme_links_exist(path: str) -> None:
    assert (ROOT / path).is_file()


@pytest.mark.parametrize("script", SCRIPTS)
@pytest.mark.parametrize("document", [SKILL_TEXT, README_TEXT], ids=["skill", "readme"])
def test_every_flag_is_documented(script: str, document: str) -> None:
    usage = run_script(script, "--help").stdout
    flags = set(re.findall(r"--[a-z-]+", usage)) - {"--help"}
    line = next(line for line in document.splitlines() if script in line and "uv run" in line)
    assert flags <= set(re.findall(r"--[a-z-]+", line))
    assert flags or script == "check_report.py"


def test_report_template_passes_the_validator(tmp_path: Path) -> None:
    template = (SKILL / "references" / "report-template.md").read_text()
    report = re.search(r"```markdown\n(.*?)```", template, re.DOTALL)
    assert report
    (tmp_path / "RELEASE.md").write_text(report[1])
    (tmp_path / "figures").mkdir()
    for name in re.findall(r"figures/([^)]+)", report[1]):
        (tmp_path / "figures" / name).write_bytes(b"image")
    process = run_script("check_report.py", str(tmp_path))
    assert process.returncode == 0, process.stderr


def note_sample() -> dict[str, Any]:
    reference = (SKILL / "references" / "access-note.md").read_text()
    block = re.search(r"```markdown\n---\n(.*?)\n---\n", reference, re.DOTALL)
    assert block
    return yaml.safe_load(block[1])


def test_note_sample_parses_with_plain_strings() -> None:
    note = note_sample()
    assert note["never"]
    assert all(isinstance(rule, str) for rule in note["never"])
    assert note["login"]["expect"]


def test_note_sample_login_has_the_capture_shape() -> None:
    login = note_sample()["login"]
    assert {"name", "steps", "expect"} <= set(login)
    assert all("action" in step for step in login["steps"])


def test_note_sample_defines_the_request_shape() -> None:
    reference = (SKILL / "references" / "access-note.md").read_text()
    samples = re.findall(r"```yaml\n(.*?)```", reference, re.DOTALL)
    request = next(yaml.safe_load(sample) for sample in samples if "request:" in sample)
    assert {"method", "path", "json", "status"} <= set(request["create_user"]["request"])
    assert "{password}" in str(request)


@pytest.mark.parametrize(
    "path", [*sorted((SKILL / "references").glob("*.md")), SKILL / "SKILL.md"], ids=lambda path: path.name
)
def test_samples_avoid_the_refused_test_domain(path: Path) -> None:
    assert "example.test" not in path.read_text()


def test_call_has_the_mode_as_its_first_word() -> None:
    assert frontmatter()["argument-hint"].strip('"').startswith("<access|release|beta>")


def test_unknown_mode_names_the_modes_that_exist() -> None:
    section = SKILL_TEXT.split("## Resolve the mode")[1].split("Defaults:")[0]
    assert all(f"`{mode}`" in section for mode in ("access", "release", "beta"))
    assert "An\nunknown mode: name the modes that exist and stop" in section
