from typing import Any
from urllib.parse import quote

import pytest
from helpers import Capture, figure

PAGE = """<!doctype html><style>
body { margin: 0; width: 3000px; height: 3000px; }
div { position: fixed; width: 100px; }
#middle { left: 500px; top: 300px; height: 50px; }
#edge { left: 500px; top: 775px; height: 24px; }
#low { left: 800px; top: 770px; height: 16px; }
#source { left: 900px; top: 700px; height: 180px; }
</style><div id="middle">m</div><div id="edge">e</div><div id="low">l</div><div id="source">s</div>"""

URL = "data:text/html," + quote(PAGE)


def on(selector: str) -> dict[str, str]:
    return {"selector": selector}


DRAWN_OUTSIDE = {
    "removed-frame": ({"kind": "removed", "anchor": on("#middle"), "offset": {"y": 700}}, "#middle"),
    "arrow-source": ({"kind": "arrow", "anchor": on("#middle"), "from": on("#source")}, "#source"),
    "arrow-tail": ({"kind": "arrow", "anchor": on("#middle"), "offset": {"y": 600}}, "#middle"),
    "badge-radius": ({"kind": "badge", "anchor": on("#low"), "number": 1, "placement": "bottom-left"}, "#low"),
    "number-on-box": ({"kind": "arrow", "anchor": on("#low"), "number": 1, "placement": "below"}, "#low"),
    "label": ({"kind": "label", "anchor": on("#middle"), "text": "long words " * 30}, "#middle"),
    "label-on-box": ({"kind": "box", "anchor": on("#middle"), "text": "long words " * 30}, "#middle"),
}

FITTING = [
    {"kind": "box", "anchor": on("#middle"), "number": 1, "text": "Short"},
    {"kind": "arrow", "anchor": on("#middle"), "offset": {"x": -200, "y": 0}},
    {"kind": "badge", "anchor": on("#edge"), "number": 2},
    {"kind": "label", "anchor": on("#edge"), "text": "Short"},
    {"kind": "removed", "anchor": on("#middle"), "offset": {"y": 100}},
]


@pytest.mark.parametrize(("annotation", "culprit"), DRAWN_OUTSIDE.values(), ids=DRAWN_OUTSIDE.keys())
def test_everything_drawn_must_fit_the_viewport(capture: Capture, annotation: dict[str, Any], culprit: str) -> None:
    message = capture.failure(figure(annotation, url=URL, full_page=False))
    assert "is outside the viewport; scroll or resize" in message
    assert "full_page" in message
    assert culprit in message
    assert not list((capture.out / "figures").glob("*.png")) if (capture.out / "figures").exists() else True


@pytest.mark.parametrize(("annotation", "_culprit"), DRAWN_OUTSIDE.values(), ids=DRAWN_OUTSIDE.keys())
def test_full_page_figure_may_draw_past_the_viewport(
    capture: Capture, annotation: dict[str, Any], _culprit: str
) -> None:
    capture.figures(figure(annotation, url=URL))


def test_marks_that_fit_pass(capture: Capture) -> None:
    capture.figures(figure(*FITTING, url=URL, full_page=False))


HEADER = """<!doctype html><style>
body { margin: 0; height: 5000px; }
header { position: fixed; left: 0; top: 0; width: 100%; height: 60px; background: #eef; }
</style><header id="top">Top</header>"""

SCROLLED: dict[str, Any] = {
    "url": "data:text/html," + quote(HEADER),
    "full_page": False,
    "steps": [{"action": "press", "key": "End"}],
}

FIXED_HEADER_MARKS = {
    "box": {"kind": "box", "anchor": on("#top")},
    "default-arrow": {"kind": "arrow", "anchor": on("#top")},
    "badge": {"kind": "badge", "anchor": on("#top"), "number": 1},
    "label": {"kind": "label", "anchor": on("#top"), "text": "Header"},
    "numbered-box": {"kind": "box", "anchor": on("#top"), "number": 1, "text": "Header"},
}


def inside_visible(point: dict[str, float], top: float) -> bool:
    return 0 <= point["x"] <= 1280 and top <= point["y"] <= top + 800


@pytest.mark.parametrize("annotation", FIXED_HEADER_MARKS.values(), ids=FIXED_HEADER_MARKS.keys())
def test_fixed_header_after_scrolling_fits(capture: Capture, annotation: dict[str, Any]) -> None:
    mark = capture.figures(figure(annotation, **SCROLLED))["figures"][0]["marks"][0]
    top = mark["element"]["y"]
    assert top > 1000
    rectangle = mark["rectangle"]
    assert rectangle["y"] >= top
    assert rectangle["y"] + rectangle["height"] <= top + 800
    if "tail" in mark:
        assert inside_visible(mark["tail"], top)
        assert inside_visible(mark["tip"], top)


def test_all_header_marks_share_one_scrolled_shot(capture: Capture) -> None:
    capture.figures(figure(*FIXED_HEADER_MARKS.values(), **SCROLLED))


@pytest.mark.parametrize(
    "annotation",
    [
        {"kind": "arrow", "anchor": on("#top"), "offset": {"x": 0, "y": -600}},
        {"kind": "removed", "anchor": on("#top"), "offset": {"y": -600}},
    ],
    ids=["arrow-offset", "removed-offset"],
)
def test_explicit_place_outside_the_scrolled_viewport_is_still_refused(
    capture: Capture, annotation: dict[str, Any]
) -> None:
    assert "is outside the viewport" in capture.failure(figure(annotation, **SCROLLED))


def test_page_shot_keeps_page_bounds(capture: Capture) -> None:
    annotation = {"kind": "box", "anchor": on("#top")}
    mark = capture.figures(figure(annotation, url=SCROLLED["url"]))["figures"][0]["marks"][0]
    assert mark["rectangle"]["y"] == 2


def test_frame_of_an_anchor_at_the_viewport_edge_is_kept_inside(capture: Capture) -> None:
    annotation = {"kind": "box", "anchor": on("#edge")}
    mark = capture.figures(figure(annotation, url=URL, full_page=False))["figures"][0]["marks"][0]
    assert mark["rectangle"]["y"] + mark["rectangle"]["height"] == 798
