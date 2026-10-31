import math
from typing import Any
from urllib.parse import quote

import pytest
from color_helpers import ANNOTATION_HEX, DEFAULT_HEX, FIGURE_HEX, SPEC_HEX, exact, marks_of, rgb
from helpers import Capture, figure
from internals import internal
from shape_helpers import URL, callout, connector, on, shape

NUMBERED = {
    "callout": callout(number=1, side="right"),
    "ellipse": shape("ellipse", number=1),
    "underline": shape("underline", number=1),
    "highlight": shape("highlight", number=1),
    "spotlight": shape("spotlight", number=1),
    "connector": connector(number=1),
}
POINTS = {
    "ellipse": (600, 282),
    "underline": (600, 364),
    "connector": (300, 120),
    "highlight": (486, 296),
    "spotlight": (486, 296),
}
BADGE_FILL = (-10, 0)


def colored(annotation: dict[str, Any], level: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str]:
    if level == "annotation":
        return annotation | {"color": ANNOTATION_HEX}, {}, {}, ANNOTATION_HEX
    if level == "figure":
        return annotation, {"color": FIGURE_HEX}, {}, FIGURE_HEX
    if level == "spec":
        return annotation, {}, {"color": SPEC_HEX}, SPEC_HEX
    return annotation, {}, {}, DEFAULT_HEX


@pytest.mark.parametrize("kind", NUMBERED)
@pytest.mark.parametrize("level", ["default", "annotation", "figure", "spec"])
def test_new_kinds_follow_the_colour_chain(capture: Capture, kind: str, level: str) -> None:
    annotation, figure_fields, spec_fields, expected = colored(NUMBERED[kind], level)
    mark = marks_of(capture.figures(figure(annotation, url=URL, **figure_fields), **spec_fields))[0]
    assert mark["color"] == expected
    image = capture.image("01-page.png")
    badge = (round(mark["badge"]["x"]) + BADGE_FILL[0], round(mark["badge"]["y"]) + BADGE_FILL[1])
    assert exact(image, badge, rgb(expected))
    if kind == "callout":
        block = mark["rectangle"]
        assert exact(image, (round(block["x"] + block["width"]) - 4, round(block["y"]) + 4), rgb(expected))
    elif kind in {"ellipse", "underline", "connector"}:
        assert exact(image, POINTS[kind], rgb(expected))


@pytest.mark.parametrize("kind", ["ellipse", "underline", "highlight", "spotlight", "connector"])
def test_text_on_a_new_kind_draws_a_label_like_on_box(capture: Capture, kind: str) -> None:
    base = connector() if kind == "connector" else shape(kind)
    mark = marks_of(capture.figures(figure(base | {"text": "New"}, url=URL)))[0]
    assert mark["text"] == "New"
    image = capture.image("01-page.png")
    top = mark.get("top", mark["corner"]["y"])
    assert exact(image, (round(mark["corner"]["x"]) + 4, round(top) - 8 - 22), rgb(DEFAULT_HEX))


@pytest.mark.parametrize(
    ("kind", "placement", "expected"),
    [
        ("highlight", "top-right", (704, 296)),
        ("underline", "bottom-left", (496, 364)),
        ("spotlight", "inside", (514, 314)),
        ("highlight", "below", (600, 384)),
        ("ellipse", "corner", (496, 296)),
        ("ellipse", "top-right", (704, 296)),
    ],
)
def test_placement_applies_to_new_kinds(capture: Capture, kind: str, placement: str, expected: tuple[int, int]) -> None:
    mark = marks_of(capture.figures(figure(shape(kind, number=1, placement=placement), url=URL)))[0]
    assert mark["badge"] == {"x": expected[0], "y": expected[1]}


@pytest.mark.parametrize(
    ("placement", "expected"),
    [
        ("left", (600 - 104 * math.sqrt(2) - 20, 330)),
        ("right", (600 + 104 * math.sqrt(2) + 20, 330)),
        ("above", (600, 330 - 34 * math.sqrt(2) - 20)),
        ("below", (600, 330 + 34 * math.sqrt(2) + 20)),
    ],
)
def test_outside_number_clears_the_curve_of_an_ellipse(
    capture: Capture, placement: str, expected: tuple[float, float]
) -> None:
    mark = marks_of(capture.figures(figure(shape("ellipse", number=1, placement=placement), url=URL)))[0]
    assert mark["badge"]["x"] == pytest.approx(expected[0])
    assert mark["badge"]["y"] == pytest.approx(expected[1])


def test_connector_number_sits_on_the_middle_of_the_line(capture: Capture) -> None:
    mark = marks_of(capture.figures(figure(connector(number=1), url=URL)))[0]
    assert mark["badge"] == {"x": 350, "y": 120}


def test_inherited_corner_placement_on_a_connector_falls_back(capture: Capture) -> None:
    mark = marks_of(capture.figures(figure(connector(number=1), url=URL, placement="inside")))[0]
    assert mark["badge"] == {"x": 350, "y": 120}


PAGE = """<!doctype html><style>
body { margin: 0; width: 3000px; height: 3000px; }
div { position: fixed; width: 100px; }
#middle { left: 500px; top: 300px; height: 50px; }
#low { left: 800px; top: 770px; height: 16px; }
#edge { left: 1160px; top: 300px; width: 110px; height: 50px; }
#source { left: 900px; top: 700px; height: 180px; }
#all { left: 0; top: 0; width: 100%; height: 100%; }
</style><div id="middle">m</div><div id="low">l</div><div id="edge">e</div><div id="source">s</div>"""
VIEWPORT_URL = "data:text/html," + quote(PAGE)

DRAWN_OUTSIDE = {
    "ellipse-number": (shape("ellipse", "#low", number=1, placement="below"), "#low"),
    "underline-number": (shape("underline", "#low", number=1, placement="below"), "#low"),
    "highlight-number": (shape("highlight", "#low", number=1, placement="below"), "#low"),
    "spotlight-number": (shape("spotlight", "#low", number=1, placement="below"), "#low"),
    "highlight-label": (shape("highlight", "#middle", text="long words " * 30), "#middle"),
    "spotlight-label": (shape("spotlight", "#middle", text="long words " * 30), "#middle"),
    "connector-source": (shape("connector", "#middle", **{"from": on("#source")}), "#source"),
    "connector-number": (shape("connector", "#low", **{"from": on("#middle")}, number=1, placement="below"), "#low"),
    "callout-number": (callout("#low", side="above", number=1, placement="below", width=400, text="x"), "#low"),
}
FITTING = [
    shape("ellipse", "#middle", number=1, text="Short"),
    shape("underline", "#low", number=2),
    shape("highlight", "#middle"),
    shape("spotlight", "#middle"),
    shape("connector", "#middle", **{"from": on("#low")}),
    callout("#edge", side="left"),
]


@pytest.mark.parametrize(("annotation", "culprit"), DRAWN_OUTSIDE.values(), ids=DRAWN_OUTSIDE.keys())
def test_everything_new_must_fit_the_viewport(capture: Capture, annotation: dict[str, Any], culprit: str) -> None:
    message = capture.failure(figure(annotation, url=VIEWPORT_URL, full_page=False))
    assert (
        "outside the viewport" in message or "falls outside the page" in message or "number of the callout" in message
    )
    assert culprit in message


def test_marks_that_fit_pass_the_viewport_check(capture: Capture) -> None:
    capture.figures(figure(*FITTING, url=VIEWPORT_URL, full_page=False))
    assert capture.image("01-page.png").size == (1280, 800)


def test_callout_keeps_inside_the_viewport_rather_than_the_page(capture: Capture) -> None:
    message = capture.failure(figure(callout("#edge", side="right"), url=VIEWPORT_URL, full_page=False))
    assert "callout does not fit right" in message


def mark_of(**extra: Any) -> dict[str, Any]:
    point = {"x": 1, "y": 1}
    rectangle = {"x": 0, "y": 0, "width": 5, "height": 5}
    return {"badge": None, "rectangle": rectangle, "start": point, "end": point, **extra}


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("ellipse", {"frame"}),
        ("highlight", {"frame"}),
        ("spotlight", {"frame"}),
        ("underline", {"underline start", "underline end"}),
        ("connector", {"connector start", "connector end"}),
        ("callout", {"callout block", "leader start", "leader end"}),
    ],
)
def test_every_part_of_a_new_kind_is_checked_by_the_viewport(kind: str, expected: set[str]) -> None:
    parts = internal("viewport").drawn_parts(mark_of(kind=kind), None)
    assert {name for name, _ in parts} == expected


def test_ellipse_is_checked_at_its_curve_and_not_at_its_inner_rectangle() -> None:
    bounds = {"x": -20, "y": 0, "width": 50, "height": 5}
    parts = internal("viewport").drawn_parts(mark_of(kind="ellipse", bounds=bounds), None)
    assert parts[0][1].x == -20
