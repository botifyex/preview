from pathlib import Path

from playwright.sync_api import Browser, Page

from capture.failures import picture_on_failure
from capture.model import Options, Shot, Spec
from capture.scheme.panels import Captured, panel_on_page
from capture.scheme.scripts import REMOVE_OVERLAY_SCRIPT, RESTORE_HIDDEN_SCRIPT
from capture.shots import Logins, context_options


def clear_page(page: Page, selectors: list[str]) -> None:
    page.evaluate(REMOVE_OVERLAY_SCRIPT)
    for selector in selectors:
        page.locator(selector).evaluate_all(RESTORE_HIDDEN_SCRIPT)


def cleared_panel(page: Page, spec: Spec, figure: Spec, index: int, options: Options, directory: Path) -> Captured:
    where = f"figure {figure['slug']} panel {index}"
    with picture_on_failure(page, f"{figure['slug']}-panel-{index}", where, options):
        clear_page(page, spec.get("hide", []))
    return panel_on_page(page, spec, figure, index, options, directory)


def capture_path(
    browser: Browser, spec: Spec, shot: Shot, options: Options, logins: Logins, directory: Path
) -> list[Captured]:
    figure = shot.figure
    context = browser.new_context(**context_options(spec, figure, options, logins.state(shot)))
    try:
        page = context.new_page()
        return [
            cleared_panel(page, spec, figure, index, options, directory)
            for index in range(1, len(figure["panels"]) + 1)
        ]
    finally:
        context.close()
