import base64
from dataclasses import asdict
from pathlib import Path

from playwright.sync_api import Page

from capture.constants import BADGE_RADIUS
from capture.model import Spec
from capture.scheme.constants import (
    DARK_INK,
    HEADING_BAND,
    HEADING_FONT,
    LABEL_FONT,
    LABEL_PADDING,
    LIGHT_BACKGROUND,
    LIGHT_INK,
    SMALLEST_BADGE,
    STEP_ONLY_WIDTH,
    STEP_WIDTH,
)
from capture.scheme.layout import Place, Sheet
from capture.scheme.links import Drawn
from capture.scheme.panels import Captured
from capture.scheme.scripts import DRAW_SCRIPT


def ink_for(background: str) -> str:
    red, green, blue = (int(background[start : start + 2], 16) for start in (1, 3, 5))
    brightness = (299 * red + 587 * green + 114 * blue) / 1000
    return DARK_INK if brightness >= LIGHT_BACKGROUND else LIGHT_INK


def data_address(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def panel_drawing(panel: Captured, place: Place, numbered: bool, color: str) -> Spec:
    middle = place.image.y - HEADING_BAND / 2
    return {
        "href": data_address(panel.path),
        "image": asdict(place.image),
        "shown": asdict(panel.shown),
        "natural": asdict(panel.natural),
        "title": panel.title,
        "titleAt": {"x": place.frame.x + (STEP_WIDTH if numbered else 0), "y": middle},
        "step": {"x": place.frame.x + STEP_ONLY_WIDTH / 2, "y": middle, "number": str(panel.index)}
        if numbered
        else None,
        "color": color,
    }


def link_drawing(drawn: Drawn, color: str) -> Spec:
    return {
        "points": drawn.route,
        "color": color,
        "dashed": drawn.link.get("style") == "dashed",
        "label": None if drawn.label is None else {"box": asdict(drawn.label), "text": drawn.link["text"]},
    }


def badges_of(entries: list[Spec]) -> list[Spec]:
    return [
        {
            "x": mark["badge"]["x"],
            "y": mark["badge"]["y"],
            "number": mark["number"],
            "color": mark["color"],
            "radius": max(SMALLEST_BADGE, BADGE_RADIUS * entry["scale"]),
        }
        for entry in entries
        for mark in entry["marks"]
        if mark["badge"]
    ]


def draw(
    page: Page,
    sheet: Sheet,
    panels: list[Captured],
    entries: list[Spec],
    links: list[Drawn],
    background: str,
    numbered: bool,
    color: str,
) -> None:
    page.set_viewport_size({"width": int(sheet.size.width), "height": int(sheet.size.height)})
    arguments = {
        "size": asdict(sheet.size),
        "background": background,
        "ink": ink_for(background),
        "panels": [
            panel_drawing(panel, place, numbered, color) for panel, place in zip(panels, sheet.places, strict=True)
        ],
        "links": [link_drawing(drawn, color) for drawn in links],
        "badges": badges_of(entries),
        "headingFont": HEADING_FONT,
        "labelFont": LABEL_FONT,
        "labelPadding": LABEL_PADDING,
    }
    page.evaluate(DRAW_SCRIPT, arguments)
