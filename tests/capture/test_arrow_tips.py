import itertools
import math
from io import BytesIO
from typing import Any
from urllib.parse import quote

import pytest
from helpers import ACCENT, Capture, figure, near
from internals import internal
from PIL import Image
from playwright.sync_api import Page, sync_playwright
from scheme_helpers import panel, run_scheme, scheme

page_scripts = internal("page_scripts")
scheme_scripts = internal("scheme.scripts")

DARK = (16, 16, 16)
DARK_HEX = "#101010"
SCALE = 4
BEYOND = (2.6, 3, 3.3, 4, 5)
INSIDE_HEAD = 5
RETREAT = 8
LONGEST_GAP = 10
PAGE = quote(
    """<!doctype html><style>html { background: #101010; } body { margin: 0; height: 800px; }
div { position: absolute; width: 60px; height: 40px; }
#to { left: 500px; top: 400px; }
#east { left: 200px; top: 400px; }
#north { left: 500px; top: 100px; }
#diagonal { left: 200px; top: 150px; }
#steep { left: 800px; top: 700px; }
</style><div id="to"></div><div id="east"></div><div id="north"></div><div id="diagonal"></div><div id="steep"></div>"""
)
URL = "data:text/html," + PAGE
HIGH = {"width": 1280, "height": 800, "scale": SCALE}
SMALL_HIGH = {"width": 200, "height": 150, "scale": SCALE}


def direction(first: dict[str, float], second: dict[str, float]) -> tuple[float, float]:
    span = math.hypot(second["x"] - first["x"], second["y"] - first["y"])
    return ((second["x"] - first["x"]) / span, (second["y"] - first["y"]) / span)


def along(tip: dict[str, float], way: tuple[float, float], distance: float) -> tuple[int, int]:
    return (round((tip["x"] + way[0] * distance) * SCALE), round((tip["y"] + way[1] * distance) * SCALE))


def assert_clean_tip(image: Image.Image, tip: dict[str, float], way: tuple[float, float]) -> None:
    for distance in BEYOND:
        assert near(image.getpixel(along(tip, way, distance)), DARK, 12), distance
    assert near(image.getpixel(along(tip, way, -INSIDE_HEAD)), ACCENT, 12)


@pytest.mark.parametrize("origin", ["#east", "#north", "#diagonal", "#steep"])
def test_nothing_shows_beyond_an_arrow_tip(capture: Capture, origin: str) -> None:
    arrow = {"kind": "arrow", "anchor": {"selector": "#to"}, "from": {"selector": origin}}
    mark = capture.figures(figure(arrow, url=URL, viewport=HIGH))["figures"][0]["marks"][0]
    assert_clean_tip(capture.image("01-page.png"), mark["tip"], direction(mark["tail"], mark["tip"]))


def test_arrow_tip_stays_on_the_frame_of_its_target(capture: Capture) -> None:
    arrow = {"kind": "arrow", "anchor": {"selector": "#to"}, "from": {"selector": "#east"}}
    mark = capture.figures(figure(arrow, url=URL))["figures"][0]["marks"][0]
    assert mark["tip"] == {"x": 496, "y": 420}


@pytest.mark.parametrize(
    ("layout", "style"),
    [("row", "solid"), ("column", "solid"), ("row", "dashed"), ("column", "dashed")],
    ids=["row", "column", "row dashed", "column dashed"],
)
def test_nothing_shows_beyond_a_link_tip(capture: Capture, layout: str, style: str) -> None:
    links = [{"from": 1, "to": 2, "style": style}]
    entry = run_scheme(
        capture, scheme(panel(), panel(), layout=layout, links=links, background=DARK_HEX, viewport=SMALL_HIGH)
    )
    points = entry["links"][0]["points"]
    way = direction(points[-2], points[-1])
    image = capture.image("01-scheme.png")
    assert_clean_tip(image, points[-1], way)


def draw_links(page: Page, *links: dict[str, Any]) -> None:
    page.set_content("<!doctype html><html><body></body></html>")
    page.evaluate(
        scheme_scripts.DRAW_SCRIPT,
        {
            "size": {"width": 500, "height": 300},
            "background": DARK_HEX,
            "ink": "#FFFFFF",
            "panels": [],
            "links": list(links),
            "badges": [],
            "headingFont": "700 15px Arial",
            "labelFont": "700 14px Arial",
            "labelPadding": 8,
        },
    )


def link(*points: list[float], dashed: bool = False) -> dict[str, Any]:
    return {"points": list(points), "color": "#E6004C", "dashed": dashed, "label": None}


def drawn_lines(page: Page) -> list[str]:
    return page.locator("polyline").evaluate_all("(lines) => lines.map((line) => line.getAttribute('points'))")


def picture(page: Page) -> Image.Image:
    return Image.open(BytesIO(page.screenshot())).convert("RGB")


@pytest.fixture
def page() -> Any:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        yield browser.new_page(viewport={"width": 500, "height": 300})
        browser.close()


def test_only_the_last_segment_of_a_link_retreats(page: Page) -> None:
    draw_links(page, link([50, 50], [200, 50], [200, 200]))
    assert drawn_lines(page) == ["50,50 200,50 200,192"] * 2


def test_start_of_a_two_point_link_stays(page: Page) -> None:
    draw_links(page, link([50, 50], [200, 50]))
    assert drawn_lines(page) == ["50,50 192,50"] * 2


@pytest.mark.parametrize("short", [1, 4, 7, 8])
def test_short_last_segment_neither_reverses_nor_vanishes(page: Page, short: int) -> None:
    draw_links(page, link([50, 100], [200, 100], [200, 100 + short]))
    for line in drawn_lines(page):
        *_, last = [tuple(map(float, point.split(","))) for point in line.split()]
        assert last[0] == 200
        assert 100 <= last[1] <= 100 + max(0, short - RETREAT)
    image = picture(page)
    assert near(image.getpixel((120, 100)), ACCENT, 12)
    assert near(image.getpixel((200, 100 + short + 4)), DARK, 12)


def test_short_arrow_neither_reverses_nor_pokes_out(page: Page) -> None:
    mark = {
        "kind": "arrow",
        "color": "#E6004C",
        "number": None,
        "text": None,
        "tail": {"x": 100, "y": 100},
        "tip": {"x": 104, "y": 100},
    }
    page.set_content(f"<!doctype html><html style='background:{DARK_HEX}'><body></body></html>")
    area = {"x": 0, "y": 0, "width": 500, "height": 300}
    page.evaluate(
        page_scripts.DRAW_SCRIPT, {"marks": [mark], "page": {"width": 500, "height": 300}, "area": area, "radius": 14}
    )
    ends = page.locator("line").first.evaluate("(line) => [line.getAttribute('x1'), line.getAttribute('x2')]")
    assert ends == ["100", "100"]
    assert near(picture(page).getpixel((108, 100)), DARK, 12)


@pytest.mark.parametrize("length", range(60, 80, 3))
def test_dashes_reach_the_head_at_any_length(page: Page, length: int) -> None:
    draw_links(page, link([50, 100], [50 + length, 100], dashed=True))
    image = picture(page)
    colored = [x for x in range(50, 50 + length) if near(image.getpixel((x, 100)), ACCENT, 40)]
    gaps = [after - before - 1 for before, after in itertools.pairwise(colored)]
    assert max(gaps) <= LONGEST_GAP
    assert colored[-1] >= 50 + length - RETREAT
