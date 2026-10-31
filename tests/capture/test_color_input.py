import json
from collections.abc import Callable
from typing import Any

import pytest
from color_helpers import (
    ANNOTATION_HEX,
    DEFAULT_HEX,
    FIGURE_HEX,
    FRAME_POINT,
    REMOVED_HEX,
    SPEC_HEX,
    exact,
    marks_of,
    removed,
    rgb,
)
from helpers import Capture, box, figure
from internals import internal

UNREACHABLE = "http://127.0.0.1:9/"


@pytest.mark.parametrize("written", ["#7a00cc", "#7A00cC", "#7A00CC"])
@pytest.mark.parametrize("level", ["annotation", "figure", "spec"])
def test_colour_is_case_insensitive_and_recorded_in_capitals(capture: Capture, written: str, level: str) -> None:
    annotation = box("#save", color=written) if level == "annotation" else box("#save")
    fields = {"color": written} if level == "figure" else {}
    extra = {"color": written} if level == "spec" else {}
    manifest = capture.figures(figure(annotation, **fields), **extra)
    assert marks_of(manifest)[0]["color"] == ANNOTATION_HEX
    assert exact(capture.image("01-page.png"), FRAME_POINT, rgb(ANNOTATION_HEX))


LEVELS: dict[str, tuple[Callable[[Any], dict[str, Any]], str]] = {
    "spec": (lambda value: {"figures": [figure()], "color": value}, "spec:"),
    "figure": (lambda value: {"figures": [figure(color=value)]}, "figure 1"),
    "annotation": (lambda value: {"figures": [figure(box("#save", color=value))]}, "annotation 1"),
    "removed": (lambda value: {"figures": [figure(removed(color=value))]}, "annotation 1"),
    "before": (
        lambda value: {"figures": [figure(before_url="old.html", before_annotations=[box("#legacy", color=value)])]},
        "before annotation 1",
    ),
}
BAD_FORMS = ["red", "#FFF", "#GGGGGG", 123, "", None, True, ["#E6004C"], "E6004C", "#E6004C00", "#E6004C\n", " #E6004C"]


@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize("value", BAD_FORMS, ids=repr)
def test_invalid_colour_fails_before_the_browser_and_names_its_level(capture: Capture, level: str, value: Any) -> None:
    build, name = LEVELS[level]
    process = capture.run({**build(value), "base_url": UNREACHABLE})
    assert process.returncode == 1
    assert process.stderr.startswith("error: ")
    assert name in process.stderr
    assert "color must be #RRGGBB" in process.stderr
    assert "Traceback" not in process.stderr
    assert not capture.out.exists()


def spec_colors(*figures: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {"figures": list(figures), **extra}


@pytest.mark.parametrize(
    ("written", "drawn"),
    [
        (spec_colors(figure(box("#save"))), [DEFAULT_HEX]),
        (spec_colors(figure(box("#save"), removed()), color="#0050c8"), [SPEC_HEX, REMOVED_HEX]),
        (spec_colors(figure(box("#save"), color="#008040")), [FIGURE_HEX]),
        (
            spec_colors(figure(box("#save", color="#7a00cc"), removed(color="#7A00cC"))),
            [ANNOTATION_HEX, ANNOTATION_HEX],
        ),
    ],
    ids=["none", "spec", "figure", "annotation"],
)
def test_saved_spec_keeps_colour_only_where_written(
    capture: Capture, site: str, written: dict[str, Any], drawn: list[str]
) -> None:
    process = capture.run(written)
    assert process.returncode == 0, process.stderr
    folder = capture.out / "figures"
    assert json.loads((folder / "spec.json").read_text()) == {"environment": "test", "base_url": site, **written}
    assert [mark["color"] for mark in marks_of(json.loads((folder / "manifest.json").read_text()))] == drawn


def test_resolver_serves_new_kinds_and_levels() -> None:
    resolve_color = internal("colors").resolve_color
    panel = {"color": "#123456"}
    assert resolve_color("future", {}) == DEFAULT_HEX
    assert resolve_color("future", {}, panel, {"color": SPEC_HEX}) == "#123456"
    assert resolve_color("future", {"color": "#abcdef"}, panel) == "#ABCDEF"
    assert resolve_color("removed", {}, panel) == REMOVED_HEX
    assert resolve_color("removed", {"color": "#abcdef"}, panel) == "#ABCDEF"
