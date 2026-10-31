import struct
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import Browser, Page

from capture.annotate import annotate, hide_elements, measure
from capture.constants import DEFAULT_VIEWPORT
from capture.failures import picture_on_failure
from capture.locators import single_visible
from capture.model import Box, CaptureFailure, Options, Shot, Spec, demand
from capture.scheme.constants import CROP_PADDING, INHERITED_FIELDS
from capture.scheme.layout import Size
from capture.scheme.routing import overlaps
from capture.scheme.scripts import OVERLAY_BOUNDS_SCRIPT
from capture.scheme.validation import panel_identity
from capture.shots import Logins, context_options, with_inherited
from capture.steps import open_url, run_steps

PNG_SIZE_START = 16
PNG_SIZE_END = 24


@dataclass(frozen=True)
class Picture:
    marks: list[Spec]
    origin: tuple[float, float]
    element: Box | None
    url: str


@dataclass(frozen=True)
class Captured:
    index: int
    identity: str | int
    title: str
    path: Path
    pixel_ratio: float
    natural: Size
    shown: Box
    picture: Picture

    @property
    def located(self) -> Box:
        left, top = self.picture.origin
        return Box(self.shown.x + left, self.shown.y + top, self.shown.width, self.shown.height)


def panel_settings(figure: Spec, panel: Spec) -> Spec:
    inherited = {field: figure[field] for field in INHERITED_FIELDS if field in figure}
    return {"full_page": False, **inherited, **panel}


def panel_shot(figure: Spec, panel: Spec, index: int) -> Shot:
    name = f"{figure['slug']}-panel-{index}"
    settings = panel_settings(figure, panel)
    return Shot(name, panel["url"], panel.get("steps", []), panel.get("annotations", []), settings, "panel")


def natural_size(path: Path, pixel_ratio: float) -> Size:
    with path.open("rb") as stream:
        header = stream.read(PNG_SIZE_END)
    width, height = struct.unpack(">II", header[PNG_SIZE_START:PNG_SIZE_END])
    return Size(width / pixel_ratio, height / pixel_ratio)


def cropped(element: Box, padding: float, origin: tuple[float, float], natural: Size, where: str) -> Box:
    left, top = element.x - origin[0], element.y - origin[1]
    within = Box(left, top, element.width, element.height).inside(0, 0, natural.width, natural.height)
    demand(within, f"{where}: crop falls outside the picture, use full_page or a larger viewport")
    near_x, near_y = max(0, left - padding), max(0, top - padding)
    far_x = min(natural.width, left + element.width + padding)
    far_y = min(natural.height, top + element.height + padding)
    return Box(near_x, near_y, far_x - near_x, far_y - near_y)


def demand_inside_crop(inside: bool, where: str) -> None:
    demand(inside, f"{where}: marks reach past the crop, raise crop_padding or crop a larger element")


def demand_marks_inside(page: Page, shown: Box, origin: tuple[float, float], where: str) -> None:
    bounds = page.evaluate(OVERLAY_BOUNDS_SCRIPT)
    if bounds is None:
        return
    drawn = Box(bounds["x"] - origin[0], bounds["y"] - origin[1], bounds["width"], bounds["height"])
    demand_inside_crop(drawn.inside(shown.x, shown.y, shown.right, shown.bottom), where)


def demand_connector_ends_shown(marks: list[Spec], shown: Box, origin: tuple[float, float], where: str) -> None:
    for mark in marks:
        if mark["kind"] != "connector":
            continue
        for end in (Box(**mark["element"]), Box(**mark["source"])):
            placed = Box(end.x - origin[0], end.y - origin[1], end.width, end.height)
            demand_inside_crop(overlaps(placed, shown, 0), where)


def open_panel(page: Page, url: str, where: str, timeout: int) -> None:
    try:
        open_url(page, url, timeout)
    except CaptureFailure as failure:
        raise CaptureFailure(f"{where}: {failure}") from failure


def shoot(page: Page, spec: Spec, shot: Shot, crop: Spec | None, path: Path, where: str, options: Options) -> Picture:
    full_page, hide = shot.figure["full_page"], spec.get("hide", [])
    open_panel(page, urljoin(spec["base_url"], shot.url), where, options.timeout)
    run_steps(page, shot.steps, spec["base_url"], where, options.timeout)
    locator = None if crop is None else single_visible(page, crop, f"{where} crop", options.timeout)
    if locator is not None:
        locator.scroll_into_view_if_needed(timeout=options.timeout)
    marks, page_size = annotate(page, with_inherited(spec, shot), full_page, hide, where, options.timeout)
    hide_elements(page, hide)
    element = None if locator is None or crop is None else measure(locator, crop, f"{where} crop")
    page.screenshot(path=str(path), full_page=full_page, animations="disabled", timeout=options.timeout)
    origin = (0, 0) if full_page else (page_size["left"], page_size["top"])
    return Picture(marks, origin, element, page.url)


def shown_area(page: Page, panel: Spec, picture: Picture, natural: Size, where: str) -> Box:
    if picture.element is None:
        return Box(0, 0, natural.width, natural.height)
    padding = panel.get("crop_padding", CROP_PADDING)
    shown = cropped(picture.element, padding, picture.origin, natural, where)
    demand_marks_inside(page, shown, picture.origin, where)
    demand_connector_ends_shown(picture.marks, shown, picture.origin, where)
    return shown


def capture_panel(
    browser: Browser, spec: Spec, figure: Spec, index: int, options: Options, logins: Logins, directory: Path
) -> Captured:
    panel = figure["panels"][index - 1]
    shot = panel_shot(figure, panel, index)
    where = f"figure {figure['slug']} panel {index}"
    pixel_ratio = {**DEFAULT_VIEWPORT, **shot.figure.get("viewport", {})}["scale"]
    path = directory / f"{index}.png"
    context = browser.new_context(**context_options(spec, shot.figure, options, logins.state(shot)))
    try:
        page = context.new_page()
        with picture_on_failure(page, shot.slug, where, options):
            picture = shoot(page, spec, shot, panel.get("crop"), path, where, options)
            natural = natural_size(path, pixel_ratio)
            shown = shown_area(page, panel, picture, natural, where)
            identity = panel_identity(panel, index)
            return Captured(index, identity, panel.get("title", ""), path, pixel_ratio, natural, shown, picture)
    finally:
        context.close()
