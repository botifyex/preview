from typing import Any

import pytest
from helpers import Capture
from scheme_helpers import panel, run_scheme

WIDE = 640
FIGURE_VIEWPORT = {"width": 600, "height": 400, "scale": 2}


def rendered(capture: Capture, figure: dict[str, Any] | None, own: dict[str, Any]) -> tuple[Any, Any, Any]:
    settings = {"slug": "scheme", "panel_width": 2000, "panels": [panel(viewport=own)]}
    entry = run_scheme(capture, {**settings, **({"viewport": figure} if figure else {})})
    rectangle = entry["panels"][0]["rectangle"]
    return rectangle["width"], rectangle["height"], entry["viewport"]["scale"]


@pytest.mark.parametrize(
    ("own", "expected"),
    [
        ({"height": 300}, (600, 300, 2)),
        ({"width": 500}, (500, 400, 2)),
        ({"scale": 1}, (600, 400, 1)),
        ({"width": 500, "height": 300, "scale": 3}, (500, 300, 3)),
    ],
    ids=["height", "width", "scale", "all"],
)
def test_panel_viewport_merges_over_the_figure(
    capture: Capture, own: dict[str, Any], expected: tuple[int, int, int]
) -> None:
    assert rendered(capture, FIGURE_VIEWPORT, own) == expected


def test_panel_viewport_falls_back_to_the_default(capture: Capture) -> None:
    assert rendered(capture, None, {"height": 300}) == (1280, 300, 1)


def test_figure_viewport_alone_still_applies(capture: Capture) -> None:
    entry = run_scheme(
        capture, {"slug": "scheme", "viewport": FIGURE_VIEWPORT, "panel_width": WIDE, "panels": [panel()]}
    )
    assert entry["panels"][0]["rectangle"]["width"] == 600
    assert entry["viewport"]["scale"] == 2
