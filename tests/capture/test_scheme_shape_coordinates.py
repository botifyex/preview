from typing import Any

import pytest
from helpers import ACCENT, Capture, figure, near
from scheme_helpers import panel, scheme
from scheme_shape_helpers import (
    DIMMED_BLUE,
    FIGURE,
    KINDS,
    SCALE,
    SHOWN_LEFT,
    SHOWN_TOP,
    SINGLE_FIGURE,
    URL,
    VIEWPORT,
    annotation,
    composite,
    cropped,
    leaves,
    probes_of,
)

HORIZONTAL = {"x"}
VERTICAL = {"y", "top", "bottom"}
LENGTHS = {"width", "height"}


def cropped_mark(capture: Capture, kind: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    plain = figure(annotation(kind), url=URL, viewport=VIEWPORT)
    manifest = capture.figures(plain, composite(panel(), cropped(annotation(kind))))
    item = manifest["figures"][1]["panels"][1]
    return manifest["figures"][0]["marks"][0], item["marks"][0], item["rectangle"]


def expected(path: tuple[str, ...], value: Any, rectangle: dict[str, float]) -> Any:
    field = path[-1]
    if field in HORIZONTAL:
        return pytest.approx(rectangle["x"] + (value - SHOWN_LEFT) * SCALE)
    if field in VERTICAL:
        return pytest.approx(rectangle["y"] + (value - SHOWN_TOP) * SCALE)
    if field in LENGTHS:
        return pytest.approx(value * SCALE)
    return value


@pytest.mark.parametrize("kind", KINDS)
def test_every_coordinate_is_scaled_and_offset(capture: Capture, kind: str) -> None:
    page_mark, mark, rectangle = cropped_mark(capture, kind)
    shown = dict(leaves(mark))
    assert shown.keys() == dict(leaves(page_mark)).keys()
    for path, value in leaves(page_mark):
        assert shown[path] == expected(path, value, rectangle), path


@pytest.mark.parametrize("kind", KINDS)
def test_manifest_points_land_on_the_mark(capture: Capture, kind: str) -> None:
    _, mark, _ = cropped_mark(capture, kind)
    image = capture.image(FIGURE)
    for probe in probes_of(mark):
        left, top = round(probe.x) - probe.reach, round(probe.y) - probe.reach
        area = (left, top, left + 2 * probe.reach + 1, top + 2 * probe.reach + 1)
        colors = image.crop(area).get_flattened_data()
        assert any(near(pixel, probe.color) for pixel in colors), probe.name


def test_fields_that_are_not_coordinates_stay(capture: Capture) -> None:
    _, spotlight, _ = cropped_mark(capture, "spotlight")
    assert spotlight["opacity"] == 0.6
    _, callout, _ = cropped_mark(capture, "callout")
    assert callout["side"] == "above"
    assert " ".join(line["text"] for line in callout["lines"]).startswith("The export now includes")


def test_veil_measures_the_panel_it_covers(capture: Capture) -> None:
    uncropped: dict[str, Any] = {"url": URL, "viewport": VIEWPORT}
    entry = capture.figures(composite(panel(annotations=[annotation("spotlight")], **uncropped)))["figures"][0]
    item = entry["panels"][0]
    rectangle = item["rectangle"]
    assert item["marks"][0]["veil"] == {"width": rectangle["width"], "height": rectangle["height"]}
    right = int(rectangle["x"] + item["marks"][0]["veil"]["width"]) - 3
    bottom = int(rectangle["y"] + item["marks"][0]["veil"]["height"]) - 3
    assert near(capture.image(SINGLE_FIGURE).getpixel((right, bottom)), DIMMED_BLUE, 3)


def test_marks_of_a_scrolled_panel_follow_the_scroll(capture: Capture) -> None:
    deep = panel(url="scheme.html?deep#ccccff", annotations=[{"kind": "ellipse", "anchor": {"selector": "#deep"}}])
    item = capture.figures(scheme(deep))["figures"][0]["panels"][0]
    mark = item["marks"][0]
    bounds = mark["bounds"]
    assert mark["top"] == bounds["y"]
    assert mark["bottom"] == bounds["y"] + bounds["height"]
    assert item["rectangle"]["y"] <= mark["top"] <= item["rectangle"]["y"] + item["rectangle"]["height"]
    across = round(bounds["x"] + bounds["width"] / 2)
    assert any(
        near(pixel, ACCENT)
        for pixel in capture.image("01-scheme.png")
        .crop((across - 1, round(mark["top"]) - 1, across + 2, round(mark["top"]) + 2))
        .get_flattened_data()
    )
