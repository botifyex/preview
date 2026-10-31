from dataclasses import asdict

from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from capture.constants import BADGE_RADIUS, IDLE_LIMIT, STABLE_POLL
from capture.geometry import build_marks, page_area, visible_area
from capture.locators import single_visible
from capture.model import Box, CaptureFailure, Spec, demand, describe_locator
from capture.page_scripts import DRAW_SCRIPT, HIDE_SCRIPT, MEASURE_SCRIPT, PAGE_SCRIPT, SCROLL_TOP_SCRIPT, SETTLE_SCRIPT
from capture.viewport import check_viewport


def wait_idle(page: Page) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=IDLE_LIMIT)
    except PlaywrightTimeout:
        return


def settle(page: Page, where: str, timeout: int) -> None:
    wait_idle(page)
    settled = page.evaluate(SETTLE_SCRIPT, timeout)
    demand(settled, f"{where}: animations did not finish within {timeout} ms")


def measure(locator: Locator, target: Spec, where: str) -> Box:
    values = locator.evaluate(MEASURE_SCRIPT)
    demand(values, f"{where}: {describe_locator(target)} is scrolled or clipped out of view")
    box = Box(**values)
    demand(box.width > 0 and box.height > 0, f"{where}: {describe_locator(target)} has no size")
    return box


def anchors_of(annotation: Spec) -> list[Spec]:
    return [annotation[key] for key in ("anchor", "from") if key in annotation]


def stable_boxes(page: Page, pairs: list[tuple[Spec, Locator]], where: str, timeout: int) -> list[Box]:
    previous: list[Box] | None = None
    for _ in range(max(2, timeout // STABLE_POLL)):
        current = [measure(locator, target, where) for target, locator in pairs]
        if current == previous:
            return current
        previous = current
        page.wait_for_timeout(STABLE_POLL)
    raise CaptureFailure(f"{where}: anchors keep moving, geometry is not stable")


def collect_pairs(page: Page, annotations: list[Spec], where: str, timeout: int) -> list[tuple[Spec, Locator]]:
    pairs: list[tuple[Spec, Locator]] = []
    for annotation in annotations:
        for target in anchors_of(annotation):
            locator = single_visible(page, target, where, timeout)
            locator.scroll_into_view_if_needed(timeout=timeout)
            pairs.append((target, locator))
    return pairs


def hide_elements(page: Page, selectors: list[str]) -> None:
    for selector in selectors:
        page.locator(selector).evaluate_all(HIDE_SCRIPT)


def annotate(
    page: Page, annotations: list[Spec], full_page: bool, hide: list[str], where: str, timeout: int
) -> tuple[list[Spec], Spec]:
    hide_elements(page, hide)
    settle(page, where, timeout)
    pairs = collect_pairs(page, annotations, where, timeout)
    if full_page:
        page.evaluate(SCROLL_TOP_SCRIPT)
    settle(page, where, timeout)
    boxes = stable_boxes(page, pairs, where, timeout)
    page_size = page.evaluate(PAGE_SCRIPT)
    area = page_area(page_size) if full_page else visible_area(page_size)
    marks = build_marks(annotations, boxes, page_size, area, where)
    arguments = {"marks": marks, "page": page_size, "area": asdict(area), "radius": BADGE_RADIUS}
    labels = page.evaluate(DRAW_SCRIPT, arguments)
    if not full_page:
        check_viewport([target for target, _ in pairs], boxes, marks, labels, page_size, where)
    return marks, page_size
