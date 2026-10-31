import hashlib
import importlib
import json
import os
import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest
from support import SCRIPTS, run_script

ROOT = Path(__file__).resolve().parent.parent
SHOWCASE = ROOT / "examples" / "showcase"
FIGURES = SHOWCASE / "figures"
SPEC = json.loads((SHOWCASE / "spec.json").read_text())
MANIFEST = json.loads((FIGURES / "manifest.json").read_text())
README = (ROOT / "README.md").read_text()
REPORT = (SHOWCASE / "RELEASE.md").read_text()
BUILD_TIMEOUT = 300
GALLERY = "number-placements"
EXTERNAL_ADDRESS = re.compile(r"https?://")
README_IMAGE = re.compile(r'<img src="([^"]+)"|!\[[^\]]*\]\(([^)]+)\)')


def capture_module(name: str) -> ModuleType:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    return importlib.import_module(f"capture.{name}")


CONSTANTS = capture_module("constants")
SCHEME_CONSTANTS = capture_module("scheme.constants")
KINDS = sorted(CONSTANTS.ANNOTATION_FIELDS)
LAYOUTS = sorted(SCHEME_CONSTANTS.LAYOUTS)
HEADS = list(CONSTANTS.CONNECTOR_HEADS)
PLACEMENTS = sorted(CONSTANTS.PLACEMENTS)
ACTIONS = sorted(CONSTANTS.STEP_FIELDS)


def children(value: Any) -> list[Any]:
    if isinstance(value, dict):
        return list(cast("dict[str, Any]", value).values())
    return cast("list[Any]", value) if isinstance(value, list) else []


def nested(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield cast("dict[str, Any]", value)
    for item in children(value):
        yield from nested(item)


def annotations(block: dict[str, Any]) -> Iterator[dict[str, Any]]:
    for item in nested(block):
        for field in ("annotations", "before_annotations"):
            yield from item.get(field, [])


def steps(block: dict[str, Any]) -> list[dict[str, Any]]:
    return [step for item in nested(block) for step in item.get("steps", [])]


def figures_with(field: str, value: Any = True) -> list[dict[str, Any]]:
    return [figure for figure in SPEC["figures"] if any(item.get(field) == value for item in nested(figure))]


def schemes() -> list[dict[str, Any]]:
    return [figure for figure in SPEC["figures"] if "panels" in figure]


def kinds_of(block: dict[str, Any]) -> set[str]:
    return {annotation["kind"] for annotation in annotations(block)}


def layout_of(figure: dict[str, Any]) -> str:
    return figure.get("layout", "row")


def files_of(slug: str) -> list[str]:
    return [Path(entry["file"]).name for entry in MANIFEST["figures"] if entry["slug"] == slug]


def readme_images() -> list[str]:
    return [first or second for first, second in README_IMAGE.findall(README)]


def shown_in_readme(slug: str) -> bool:
    return all(any(image.endswith(name) for image in readme_images()) for name in files_of(slug))


def png_names() -> set[str]:
    return {path.name for path in FIGURES.glob("*.png")}


def fingerprints(directory: Path) -> dict[str, str]:
    files = (path for path in sorted(directory.rglob("*")) if path.is_file())
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}


def test_spec_passes_validation() -> None:
    capture_module("validation").validate_spec(SPEC)


@pytest.mark.parametrize("kind", KINDS)
def test_kind_is_showcased(kind: str) -> None:
    assert kind in kinds_of(SPEC)


@pytest.mark.parametrize("layout", LAYOUTS)
def test_layout_is_showcased(layout: str) -> None:
    assert any(layout_of(figure) == layout for figure in schemes())


@pytest.mark.parametrize("heads", HEADS)
def test_connector_heads_are_showcased(heads: str) -> None:
    assert any(mark.get("heads") == heads for mark in annotations(SPEC))


@pytest.mark.parametrize("action", ACTIONS)
def test_step_action_is_showcased(action: str) -> None:
    assert action in {step["action"] for step in steps(SPEC)}


@pytest.mark.parametrize("placement", PLACEMENTS)
def test_gallery_shows_every_placement(placement: str) -> None:
    gallery = next(figure for figure in SPEC["figures"] if figure["slug"] == GALLERY)
    assert placement in {mark["placement"] for mark in annotations(gallery)}


@pytest.mark.parametrize("field", ["offset", "from"])
def test_arrow_variant_is_showcased(field: str) -> None:
    assert any(mark["kind"] == "arrow" and field in mark for mark in annotations(SPEC))


def test_arrow_with_default_tail_is_showcased() -> None:
    assert any(mark["kind"] == "arrow" and not {"offset", "from"} & set(mark) for mark in annotations(SPEC))


def test_callout_sets_side_and_width() -> None:
    assert any(mark["kind"] == "callout" and {"side", "width"} <= set(mark) for mark in annotations(SPEC))


@pytest.mark.parametrize("locator", ["selector", "role", "text"])
def test_locator_form_is_showcased(locator: str) -> None:
    assert any(locator in item for item in nested(SPEC))


@pytest.mark.parametrize("match", ["substring", "regex"])
def test_match_form_is_showcased(match: str) -> None:
    assert figures_with("match", match)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("theme", "dark"),
        ("has_touch", True),
        ("scale", 2),
        ("full_page", True),
        ("full_page", False),
        ("login", False),
        ("continuous", True),
        ("steps_numbers", True),
        ("links", "sequence"),
        ("style", "dashed"),
    ],
)
def test_option_is_showcased(field: str, value: Any) -> None:
    assert figures_with(field, value)


@pytest.mark.parametrize(
    "field",
    [
        "before_url",
        "before_annotations",
        "columns",
        "crop",
        "crop_padding",
        "title",
        "from_mark",
        "background",
        "panel_width",
    ],
)
def test_field_is_showcased(field: str) -> None:
    assert any(field in item for figure in SPEC["figures"] for item in nested(figure))


def test_scheme_link_carries_text() -> None:
    assert any(
        link.get("text") for figure in schemes() if isinstance(figure.get("links"), list) for link in figure["links"]
    )


def test_color_is_set_at_every_level() -> None:
    assert "color" in SPEC
    assert any("color" in figure for figure in SPEC["figures"])
    assert any("color" in mark for mark in annotations(SPEC))


def test_removed_is_drawn_in_its_own_red_under_a_figure_color() -> None:
    entries = [entry for entry in MANIFEST["figures"] if entry["slug"] == "colour-levels"]
    colors = {mark["kind"]: mark["color"] for mark in entries[0]["marks"]}
    assert colors["removed"] == CONSTANTS.KIND_COLORS["removed"]
    assert colors["box"] != colors["removed"]


def test_hide_is_listed() -> None:
    assert SPEC["hide"]


def test_password_comes_from_the_environment() -> None:
    fields = [step for step in SPEC["login"]["steps"] if step.get("target", {}).get("name") == "Password"]
    assert [field["value_env"] for field in fields] == ["SHOWCASE_PASSWORD"]
    assert "value" not in fields[0]


def test_only_the_gallery_warns() -> None:
    warned = {entry["slug"] for entry in MANIFEST["figures"] if entry["warnings"]}
    assert warned == {GALLERY}


def test_site_makes_no_external_requests() -> None:
    sources = [path for path in (SHOWCASE / "site").rglob("*") if path.is_file()]
    assert sources
    assert [path.name for path in sources if EXTERNAL_ADDRESS.search(path.read_text())] == []


def test_manifest_lists_every_png_and_back() -> None:
    assert {Path(entry["file"]).name for entry in MANIFEST["figures"]} == png_names()


def test_committed_spec_copy_matches_the_spec() -> None:
    assert json.loads((FIGURES / "spec.json").read_text()) == SPEC


@pytest.mark.parametrize("image", readme_images())
def test_readme_image_exists(image: str) -> None:
    assert (ROOT / image).is_file()


@pytest.mark.parametrize("kind", KINDS)
def test_readme_shows_kind(kind: str) -> None:
    assert any(kind in kinds_of(figure) and shown_in_readme(figure["slug"]) for figure in SPEC["figures"])


@pytest.mark.parametrize("layout", LAYOUTS)
def test_readme_shows_layout(layout: str) -> None:
    assert any(layout_of(figure) == layout and shown_in_readme(figure["slug"]) for figure in schemes())


@pytest.mark.parametrize("name", sorted(png_names()))
def test_figure_is_used(name: str) -> None:
    assert name in README or f"figures/{name}" in REPORT


def test_readme_states_how_to_rebuild() -> None:
    assert "uv run examples/showcase/build.py" in README
    assert "examples/showcase/RELEASE.md" in README


def test_report_passes_the_validator() -> None:
    process = run_script("check_report.py", str(SHOWCASE))
    assert process.returncode == 0, process.stderr


def default_state() -> Path:
    cache = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(cache) / "preview" / "state"


def test_build_reproduces_the_committed_manifest(tmp_path: Path) -> None:
    before = fingerprints(SHOWCASE)
    output = tmp_path / "output"
    process = subprocess.run(
        ["uv", "run", "--quiet", str(SHOWCASE / "build.py"), "--out", str(output)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=BUILD_TIMEOUT,
        check=False,
    )
    assert process.returncode == 0, process.stderr
    assert json.loads((output / "figures" / "manifest.json").read_text()) == MANIFEST
    assert fingerprints(SHOWCASE) == before
    assert not list(default_state().glob(f"{SPEC['login']['name']}-*"))
