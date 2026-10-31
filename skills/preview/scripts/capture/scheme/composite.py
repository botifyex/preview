import tempfile
from dataclasses import asdict
from pathlib import Path

from playwright.sync_api import Browser, Page

from capture.colors import resolve_color
from capture.constants import MARK_ADVICE
from capture.model import Box, Options, Shot, Spec
from capture.scheme.constants import (
    BACKGROUND,
    HEADING_FONT,
    LABEL_FONT,
    LABEL_PADDING,
    LABEL_ROOM,
    LINKED_GAP,
    LINKED_MARGIN,
    PANEL_ADVICE,
    PANEL_WIDTH,
    PLAIN_GAP,
    PLAIN_MARGIN,
    STEP_ONLY_WIDTH,
    STEP_WIDTH,
)
from capture.scheme.drawing import draw
from capture.scheme.layout import Sheet, Size, Slot, arranged, column_count, fit_scale, fitted, refuse_oversize
from capture.scheme.links import Drawn, drawn_links, link_entry, links_of, route_links
from capture.scheme.panels import Captured, capture_panel
from capture.scheme.placement import scaled_mark
from capture.scheme.scripts import TEXT_WIDTH_SCRIPT
from capture.shots import Logins, figure_name


def text_widths(page: Page, font: str, texts: list[str]) -> list[float]:
    return page.evaluate(TEXT_WIDTH_SCRIPT, [{"font": font, "text": text} for text in texts])


def heading_width(panel: Captured, numbered: bool, title_width: float) -> float:
    if not numbered:
        return title_width
    return STEP_WIDTH + title_width if panel.title else STEP_ONLY_WIDTH


def default_gap(links: list[Spec], widths: list[float]) -> float:
    if not links:
        return PLAIN_GAP
    return max([LINKED_GAP, *(width + LABEL_ROOM + 2 * LABEL_PADDING for width in widths if width)])


def shown_size(panel: Captured) -> Size:
    return Size(panel.shown.width, panel.shown.height)


def layout_sheet(figure: Spec, panels: list[Captured], links: list[Spec], widths: list[float], page: Page) -> Sheet:
    numbered = figure.get("steps_numbers", False)
    limit = figure.get("panel_width", PANEL_WIDTH)
    titles = text_widths(page, HEADING_FONT, [panel.title for panel in panels])
    slots = [
        Slot(fitted(shown_size(panel), limit), heading_width(panel, numbered, width))
        for panel, width in zip(panels, titles, strict=True)
    ]
    columns = column_count(figure.get("layout", "row"), figure.get("columns", 1), len(panels))
    margin = LINKED_MARGIN if links else PLAIN_MARGIN
    return arranged(slots, columns, figure.get("gap", default_gap(links, widths)), margin)


def panel_entry(panel: Captured, image: Box, limit: float) -> Spec:
    scale = fit_scale(shown_size(panel), limit)
    return {
        "id": panel.identity,
        "title": panel.title or None,
        "url": panel.picture.url,
        "rectangle": asdict(image),
        "scale": scale,
        "marks": [scaled_mark(mark, panel.located, image, scale) for mark in panel.picture.marks],
    }


def warnings_of(panels: list[Captured]) -> list[str]:
    many = [f"{len(panels)} panels, keep one idea per image"] if len(panels) > PANEL_ADVICE else []
    marks = [
        f"panel {panel.index}: {len(panel.picture.marks)} marks, keep one idea per image"
        for panel in panels
        if len(panel.picture.marks) > MARK_ADVICE
    ]
    return many + marks


def scheme_entry(
    figure: Spec, number: int, sheet: Sheet, ratio: float, entries: list[Spec], links: list[Drawn]
) -> Spec:
    return {
        "number": number,
        "file": f"figures/{figure_name(number, figure['slug'])}",
        "slug": figure["slug"],
        "role": "scheme",
        "layout": figure.get("layout", "row"),
        "viewport": {"width": sheet.size.width, "height": sheet.size.height, "scale": ratio},
        "panels": entries,
        "links": [link_entry(drawn) for drawn in links],
    }


def compose(
    page: Page, spec: Spec, figure: Spec, panels: list[Captured], ratio: float, number: int
) -> tuple[Spec, Path]:
    slug = figure["slug"]
    links = links_of(figure, [panel.identity for panel in panels])
    widths = text_widths(page, LABEL_FONT, [link.get("text", "") for link in links])
    sheet = layout_sheet(figure, panels, links, widths, page)
    refuse_oversize(sheet.size, ratio, f"figure {slug}")
    limit = figure.get("panel_width", PANEL_WIDTH)
    entries = [panel_entry(panel, place.image, limit) for panel, place in zip(panels, sheet.places, strict=True)]
    drawn = drawn_links(links, route_links(links, entries, sheet, slug), widths, sheet, slug)
    numbered = figure.get("steps_numbers", False)
    color = resolve_color("scheme", figure, spec)
    draw(page, sheet, panels, entries, drawn, figure.get("background", BACKGROUND), numbered, color)
    return scheme_entry(figure, number, sheet, ratio, entries, drawn), Path(figure_name(number, slug))


def composed(
    browser: Browser, spec: Spec, figure: Spec, panels: list[Captured], number: int, options: Options, staging: Path
) -> Spec:
    ratio = max(panel.pixel_ratio for panel in panels)
    context = browser.new_context(device_scale_factor=ratio)
    try:
        page = context.new_page()
        page.set_content("<!doctype html><html><body></body></html>")
        entry, name = compose(page, spec, figure, panels, ratio, number)
        page.screenshot(path=str(staging / name), animations="disabled", timeout=options.timeout)
    finally:
        context.close()
    return {**entry, "warnings": warnings_of(panels)}


def capture_scheme(
    browser: Browser, spec: Spec, shot: Shot, number: int, options: Options, logins: Logins, staging: Path
) -> Spec:
    figure = shot.figure
    with tempfile.TemporaryDirectory(dir=options.output, prefix=".capture-panels-") as directory:
        panels = [
            capture_panel(browser, spec, figure, index, options, logins, Path(directory))
            for index in range(1, len(figure["panels"]) + 1)
        ]
        return composed(browser, spec, figure, panels, number, options, staging)
