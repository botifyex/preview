import math
from typing import cast
from urllib.parse import quote

import pytest
from color_helpers import exact, marks_of
from helpers import ACCENT, Capture, box, figure, near
from shape_helpers import (
    TARGET,
    TARGET_COLOR,
    TARGET_FRAME,
    URL,
    WHITE,
    blend,
    connector,
    contrast,
    on,
    shape,
)

LINE_Y = 120
CENTER = (600, 330)
HIGHLIGHT_OPACITY = 0.25
SPOTLIGHT_OPACITY = 0.6
BLACK = (0, 0, 0)


def test_ellipse_passes_outside_every_corner_of_the_element(capture: Capture) -> None:
    mark = marks_of(capture.figures(figure(shape("ellipse"), url=URL)))[0]
    assert mark["element"] == TARGET
    assert mark["rectangle"] == TARGET_FRAME
    reach_x, reach_y = 104 * math.sqrt(2), 34 * math.sqrt(2)
    assert mark["bounds"]["width"] == pytest.approx(2 * reach_x)
    assert mark["bounds"]["height"] == pytest.approx(2 * reach_y)
    image = capture.image("01-page.png")
    on_curve = [
        (round(600 - reach_x), 330),
        (round(600 + reach_x), 330),
        (600, round(330 - reach_y)),
        (600, round(330 + reach_y)),
        (496, 296),
        (704, 364),
    ]
    for point in on_curve:
        assert near(image.getpixel(point), ACCENT), point
    for corner in [(500, 300), (699, 300), (500, 359), (699, 359)]:
        assert image.getpixel(corner) == TARGET_COLOR, corner


def test_underline_runs_under_the_element_and_leaves_it_clean(capture: Capture) -> None:
    mark = marks_of(capture.figures(figure(shape("underline"), url=URL)))[0]
    assert mark["start"] == {"x": 500, "y": 364}
    assert mark["end"] == {"x": 700, "y": 364}
    image = capture.image("01-page.png")
    for x in (502, 600, 698):
        assert near(image.getpixel((x, 364)), ACCENT), x
    assert image.getpixel((490, 364)) == WHITE
    assert image.getpixel((710, 364)) == WHITE
    assert image.getpixel(CENTER) == TARGET_COLOR
    assert image.getpixel((600, 300)) == TARGET_COLOR


def test_highlight_tints_the_element_keeps_text_readable_and_has_no_frame(capture: Capture) -> None:
    mark = marks_of(capture.figures(figure(shape("highlight"), url=URL)))[0]
    assert mark["rectangle"] == TARGET_FRAME
    assert mark["opacity"] == HIGHLIGHT_OPACITY
    image = capture.image("01-page.png")
    tint = blend(TARGET_COLOR, ACCENT, HIGHLIGHT_OPACITY)
    ink = blend(BLACK, ACCENT, HIGHLIGHT_OPACITY)
    assert near(image.getpixel((520, 330)), tint, 2)
    assert near(image.getpixel((580, 330)), ink, 2)
    assert contrast(image.getpixel((580, 330)), image.getpixel((520, 330))) >= 4.5
    assert near(image.getpixel((498, 330)), blend(WHITE, ACCENT, HIGHLIGHT_OPACITY), 2)
    assert image.getpixel((494, 330)) == WHITE


def test_highlight_on_a_dark_page_stays_visible_and_readable(capture: Capture) -> None:
    dark = "data:text/html," + quote(
        "<!doctype html><style>html{background:#101010}#t,#i{position:absolute}"
        "#t{left:100px;top:100px;width:200px;height:60px}#i{left:120px;top:120px;width:40px;height:20px;"
        "background:#eee}</style><div id=t></div><div id=i></div>"
    )
    capture.figures(figure(shape("highlight", "#t"), url=dark, theme="dark"))
    image = capture.image("01-page.png")
    red, _, _ = cast("tuple[int, int, int]", image.getpixel((200, 130)))
    assert red - 16 >= 40
    assert contrast(image.getpixel((140, 130)), image.getpixel((200, 130))) >= 4.5


def test_spotlight_dims_the_whole_page_but_the_hole(capture: Capture) -> None:
    mark = marks_of(capture.figures(figure(shape("spotlight"), url=URL)))[0]
    assert mark["rectangle"] == TARGET_FRAME
    assert mark["opacity"] == SPOTLIGHT_OPACITY
    image = capture.image("01-page.png")
    dimmed = blend(WHITE, BLACK, SPOTLIGHT_OPACITY)
    for point in [(5, 5), (1275, 5), (5, 995), (1275, 995), (490, 330), (710, 330)]:
        assert near(image.getpixel(point), dimmed, 1), point
    assert image.getpixel(CENTER) == TARGET_COLOR
    assert image.getpixel((500, 300)) == TARGET_COLOR
    assert image.getpixel((580, 330)) == BLACK


def test_spotlight_on_a_viewport_figure_covers_the_viewport(capture: Capture) -> None:
    capture.figures(figure(shape("spotlight"), url=URL, full_page=False, viewport={"width": 900, "height": 500}))
    image = capture.image("01-page.png")
    assert image.size == (900, 500)
    dimmed = blend(WHITE, BLACK, SPOTLIGHT_OPACITY)
    for point in [(1, 1), (898, 1), (1, 498), (898, 498)]:
        assert near(image.getpixel(point), dimmed, 1), point
    assert image.getpixel(CENTER) == TARGET_COLOR


def test_spotlight_listed_last_is_still_drawn_under_other_marks(capture: Capture) -> None:
    capture.figures(figure(box("#first"), shape("spotlight"), url=URL))
    image = capture.image("01-page.png")
    assert exact(image, (96, 120), ACCENT)


def test_highlight_listed_last_does_not_tint_an_earlier_frame(capture: Capture) -> None:
    capture.figures(figure(box("#target"), shape("highlight"), url=URL))
    image = capture.image("01-page.png")
    assert exact(image, (496, 330), ACCENT)


def test_spotlight_number_and_label_stay_above_the_dimming(capture: Capture) -> None:
    capture.figures(figure(shape("spotlight", number=1, text="New"), url=URL))
    image = capture.image("01-page.png")
    assert exact(image, (486, 296), ACCENT)
    assert exact(image, (520, 266), ACCENT)


def test_connector_joins_the_edges_of_both_elements(capture: Capture) -> None:
    mark = marks_of(capture.figures(figure(connector(), url=URL)))[0]
    assert mark["heads"] == "none"
    assert mark["start"] == {"x": 204, "y": LINE_Y}
    assert mark["end"] == {"x": 496, "y": LINE_Y}
    assert mark["source"] == {"x": 100, "y": 100, "width": 100, "height": 40}
    image = capture.image("01-page.png")
    for x in (206, 350, 494):
        assert near(image.getpixel((x, LINE_Y)), ACCENT), x
    assert image.getpixel((150, LINE_Y)) == (238, 238, 238)
    assert image.getpixel((550, LINE_Y)) == (238, 238, 238)


@pytest.mark.parametrize(
    ("heads", "at_end", "at_start"),
    [(None, False, False), ("none", False, False), ("end", True, False), ("both", True, True)],
)
def test_connector_heads_sit_where_asked(capture: Capture, heads: str | None, at_end: bool, at_start: bool) -> None:
    annotation = connector(**({"heads": heads} if heads else {}))
    capture.figures(figure(annotation, url=URL))
    image = capture.image("01-page.png")
    assert near(image.getpixel((488, LINE_Y + 2)), ACCENT, 60) is at_end
    assert near(image.getpixel((212, LINE_Y + 2)), ACCENT, 60) is at_start


def test_connector_head_hides_the_round_cap_of_the_line(capture: Capture) -> None:
    dark = "data:text/html," + quote(
        "<!doctype html><style>html{background:#101010}div{position:absolute;top:100px;width:100px;height:40px}"
        "#a{left:100px}#b{left:500px}</style><div id=a></div><div id=b></div>"
    )
    annotation = {"kind": "connector", "anchor": on("#b"), "from": on("#a"), "heads": "both"}
    capture.figures(figure(annotation, url=dark, theme="dark"))
    image = capture.image("01-page.png")
    assert image.getpixel((499, LINE_Y)) == (16, 16, 16)
    assert image.getpixel((201, LINE_Y)) == (16, 16, 16)


@pytest.mark.parametrize("source", ["#target", "#ink", "#second"], ids=["nested", "inside", "itself"])
def test_connector_between_overlapping_elements_fails(capture: Capture, source: str) -> None:
    anchor = "#second" if source == "#second" else "#target"
    annotation = shape("connector", anchor, **{"from": on(source)})
    assert "has no room" in capture.failure(figure(annotation, url=URL))
