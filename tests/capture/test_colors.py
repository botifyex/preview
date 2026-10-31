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
from helpers import ACCENT, REMOVED, Capture, box, figure, near
from PIL import Image

WHITE = (255, 255, 255)
BEFORE_FRAME_POINT = (96, 540)
REMOVED_BADGE_POINT = (86, 596)
REMOVED_LABEL_POINT = (120, 570)
REMOVED_EDGE_Y = 596


def arrow(**extra: Any) -> dict[str, Any]:
    return {"kind": "arrow", "anchor": {"selector": "#save"}, "offset": {"x": -180, "y": 0}, **extra}


def badge() -> dict[str, Any]:
    return {"kind": "badge", "anchor": {"selector": "#save"}, "number": 1}


def label() -> dict[str, Any]:
    return {"kind": "label", "anchor": {"selector": "#save"}, "text": "New"}


PARTS = {
    "box-frame": (box("#save"), FRAME_POINT),
    "box-badge": (box("#save", number=1), (286, 196)),
    "box-label": (box("#save", text="New"), (300, 170)),
    "arrow-line": (arrow(), (230, 224)),
    "arrow-head": (arrow(), (286, 226)),
    "arrow-badge": (arrow(number=1), (190, 224)),
    "arrow-label": (arrow(text="New"), (204, 198)),
    "badge": (badge(), (286, 196)),
    "label": (label(), (300, 170)),
}


def colored_at_level(annotation: dict[str, Any], level: str) -> tuple[dict[str, Any], dict[str, Any], str]:
    if level == "annotation":
        return annotation | {"color": ANNOTATION_HEX}, {}, ANNOTATION_HEX
    if level == "figure":
        return annotation, {"color": FIGURE_HEX}, FIGURE_HEX
    if level == "spec":
        return annotation, {}, SPEC_HEX
    return annotation, {}, DEFAULT_HEX


@pytest.mark.parametrize("part", PARTS)
@pytest.mark.parametrize("level", ["default", "annotation", "figure", "spec"])
def test_every_part_of_a_mark_takes_the_colour(capture: Capture, part: str, level: str) -> None:
    annotation, point = PARTS[part]
    annotation, figure_fields, expected = colored_at_level(annotation, level)
    extra = {"color": SPEC_HEX} if level == "spec" else {}
    manifest = capture.figures(figure(annotation, **figure_fields), **extra)
    assert marks_of(manifest)[0]["color"] == expected
    assert exact(capture.image("01-page.png"), point, rgb(expected))


def test_default_accent_is_the_new_red_magenta(capture: Capture) -> None:
    capture.figures(figure(box("#save")))
    assert rgb(DEFAULT_HEX) == ACCENT
    assert not near(capture.image("01-page.png").getpixel(FRAME_POINT), (230, 0, 126), 40)


@pytest.mark.parametrize(
    ("spec_level", "figure_level", "annotation_level", "expected"),
    [
        (None, None, None, DEFAULT_HEX),
        (SPEC_HEX, None, None, SPEC_HEX),
        (SPEC_HEX, FIGURE_HEX, None, FIGURE_HEX),
        (SPEC_HEX, FIGURE_HEX, ANNOTATION_HEX, ANNOTATION_HEX),
        (None, FIGURE_HEX, None, FIGURE_HEX),
        (SPEC_HEX, None, ANNOTATION_HEX, ANNOTATION_HEX),
    ],
)
def test_nearest_colour_wins(
    capture: Capture, spec_level: str | None, figure_level: str | None, annotation_level: str | None, expected: str
) -> None:
    annotation = box("#save", **({"color": annotation_level} if annotation_level else {}))
    fields = {"color": figure_level} if figure_level else {}
    extra = {"color": spec_level} if spec_level else {}
    manifest = capture.figures(figure(annotation, **fields), **extra)
    assert marks_of(manifest)[0]["color"] == expected
    assert exact(capture.image("01-page.png"), FRAME_POINT, rgb(expected))


def test_marks_of_one_figure_keep_their_own_colours(capture: Capture) -> None:
    manifest = capture.figures(figure(box("#save", color=ANNOTATION_HEX), box("#block"), color=FIGURE_HEX))
    assert [mark["color"] for mark in marks_of(manifest)] == [ANNOTATION_HEX, FIGURE_HEX]
    image = capture.image("01-page.png")
    assert exact(image, FRAME_POINT, rgb(ANNOTATION_HEX))
    assert exact(image, BEFORE_FRAME_POINT, rgb(FIGURE_HEX))


def white_inside(image: Image.Image, left: int, top: int, right: int, bottom: int) -> bool:
    return any(exact(image, (x, y), WHITE) for x in range(left, right) for y in range(top, bottom))


@pytest.mark.parametrize("color", [None, ANNOTATION_HEX], ids=["default", "custom"])
def test_halo_and_white_text_stay(capture: Capture, color: str | None) -> None:
    fields = {"color": color} if color else {}
    manifest = capture.figures(figure(box("#save", number=1, text="New", **fields)))
    chosen = rgb(marks_of(manifest)[0]["color"])
    image = capture.image("01-page.png")
    assert chosen == rgb(color or DEFAULT_HEX)
    assert exact(image, FRAME_POINT, chosen)
    assert near(image.getpixel((293, 224)), WHITE, 3)
    assert near(image.getpixel((282, 196)), WHITE, 3)
    assert white_inside(image, 290, 189, 303, 203)
    assert white_inside(image, 324, 168, 352, 184)


def assert_removed_drawn_in(image: Image.Image, color: tuple[int, int, int]) -> None:
    assert exact(image, REMOVED_BADGE_POINT, color)
    assert exact(image, REMOVED_LABEL_POINT, color)
    painted = [exact(image, (x, REMOVED_EDGE_Y), color) for x in range(120, 330)]
    assert any(painted), "removed edge must use the colour"
    assert not all(painted), "removed edge must stay dashed"


def test_removed_defaults_to_its_own_red(capture: Capture) -> None:
    manifest = capture.figures(figure(removed(number=1, text="Was here")))
    assert marks_of(manifest)[0]["color"] == REMOVED_HEX
    assert rgb(REMOVED_HEX) == REMOVED
    assert_removed_drawn_in(capture.image("01-page.png"), REMOVED)


@pytest.mark.parametrize(
    ("figure_fields", "extra", "inherited"),
    [
        ({"color": FIGURE_HEX}, {}, FIGURE_HEX),
        ({}, {"color": SPEC_HEX}, SPEC_HEX),
        ({"color": FIGURE_HEX}, {"color": SPEC_HEX}, FIGURE_HEX),
    ],
    ids=["figure", "spec", "both"],
)
def test_inherited_colour_does_not_recolour_removed(
    capture: Capture, figure_fields: dict[str, str], extra: dict[str, str], inherited: str
) -> None:
    manifest = capture.figures(figure(removed(number=1, text="Was here"), box("#save"), **figure_fields), **extra)
    assert [mark["color"] for mark in marks_of(manifest)] == [REMOVED_HEX, inherited]
    image = capture.image("01-page.png")
    assert_removed_drawn_in(image, REMOVED)
    assert exact(image, FRAME_POINT, rgb(inherited))


def test_removed_takes_a_colour_set_on_itself(capture: Capture) -> None:
    annotation = removed(number=1, text="Was here", color=ANNOTATION_HEX)
    manifest = capture.figures(figure(annotation, color=FIGURE_HEX), color=SPEC_HEX)
    assert marks_of(manifest)[0]["color"] == ANNOTATION_HEX
    assert_removed_drawn_in(capture.image("01-page.png"), rgb(ANNOTATION_HEX))


@pytest.mark.parametrize(
    ("spec_level", "figure_level", "annotation_level", "expected"),
    [
        (None, None, None, DEFAULT_HEX),
        (SPEC_HEX, None, None, SPEC_HEX),
        (SPEC_HEX, FIGURE_HEX, None, FIGURE_HEX),
        (SPEC_HEX, FIGURE_HEX, ANNOTATION_HEX, ANNOTATION_HEX),
    ],
)
def test_before_shot_inherits_the_same_chain(
    capture: Capture,
    site: str,
    spec_level: str | None,
    figure_level: str | None,
    annotation_level: str | None,
    expected: str,
) -> None:
    annotation = box("#legacy", **({"color": annotation_level} if annotation_level else {}))
    fields = {"color": figure_level} if figure_level else {}
    extra = {"color": spec_level} if spec_level else {}
    manifest = capture.figures(figure(before_url=f"{site}old.html", before_annotations=[annotation], **fields), **extra)
    assert manifest["figures"][0]["role"] == "before"
    assert marks_of(manifest)[0]["color"] == expected
    assert exact(capture.image("01-page-before.png"), BEFORE_FRAME_POINT, rgb(expected))


def test_removed_in_a_before_shot_stays_red(capture: Capture, site: str) -> None:
    annotation = {"kind": "removed", "anchor": {"selector": "#legacy"}, "offset": {"y": 100}}
    manifest = capture.figures(figure(before_url=f"{site}old.html", before_annotations=[annotation], color=FIGURE_HEX))
    assert marks_of(manifest)[0]["color"] == REMOVED_HEX
