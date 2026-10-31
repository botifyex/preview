import os
from urllib.parse import urljoin

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page

from capture.locators import single_visible
from capture.model import CaptureFailure, Spec, demand


def secret_value(step: Spec, where: str) -> str:
    if "value" in step:
        return step["value"]
    name = step["value_env"]
    demand(name in os.environ, f"{where}: environment variable {name} is not set")
    return os.environ[name]


def open_url(page: Page, url: str, timeout: int) -> None:
    response = page.goto(url, timeout=timeout)
    if response is not None:
        demand(response.ok, f"{url} answered with status {response.status}")


def fill(page: Page, step: Spec, where: str, timeout: int) -> None:
    locator = single_visible(page, step["target"], where, timeout)
    literal = "value" in step and locator.get_attribute("type") == "password"
    demand(not literal, f"{where}: a password needs value_env, the spec is saved with the output")
    locator.fill(secret_value(step, where), timeout=timeout)


def press(page: Page, step: Spec, where: str, timeout: int) -> None:
    if "target" in step:
        single_visible(page, step["target"], where, timeout).press(step["key"], timeout=timeout)
    else:
        page.keyboard.press(step["key"])


def perform(page: Page, step: Spec, base_url: str, where: str, timeout: int) -> None:
    kind = step["action"]
    if kind == "goto":
        open_url(page, urljoin(base_url, step["url"]), timeout)
    elif kind == "fill":
        fill(page, step, where, timeout)
    elif kind == "click":
        single_visible(page, step["target"], where, timeout).click(timeout=timeout)
    elif kind == "hover":
        single_visible(page, step["target"], where, timeout).hover(timeout=timeout)
    elif kind == "press":
        press(page, step, where, timeout)
    elif "milliseconds" in step:
        page.wait_for_timeout(step["milliseconds"])
    else:
        single_visible(page, step["target"], where, timeout)


def run_steps(page: Page, steps: list[Spec], base_url: str, where: str, timeout: int) -> None:
    for index, step in enumerate(steps, 1):
        location = f"{where} step {index} ({step['action']})"
        try:
            perform(page, step, base_url, location, timeout)
        except PlaywrightError as failure:
            first_line = str(failure).splitlines()[0]
            raise CaptureFailure(f"{location}: {first_line}") from failure
