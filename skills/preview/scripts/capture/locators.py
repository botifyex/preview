import re

from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from capture.model import CaptureFailure, Spec, demand, describe_locator


def text_query(target: Spec, text: str) -> tuple[str | re.Pattern[str], bool]:
    kind = target.get("match", "exact")
    if kind == "regex":
        return (re.compile(text), False)
    return (text, kind == "exact")


def locator_of(page: Page, target: Spec) -> Locator:
    if "selector" in target:
        return page.locator(target["selector"])
    if "role" in target:
        if "name" not in target:
            return page.get_by_role(target["role"])
        name, exact = text_query(target, target["name"])
        return page.get_by_role(target["role"], name=name, exact=exact)
    text, exact = text_query(target, target["text"])
    return page.get_by_text(text, exact=exact)


def single_visible(page: Page, target: Spec, where: str, timeout: int) -> Locator:
    locator = locator_of(page, target).filter(visible=True)
    description = describe_locator(target)
    try:
        locator.first.wait_for(state="visible", timeout=timeout)
    except PlaywrightTimeout as failure:
        raise CaptureFailure(f"{where}: {description} matched no visible element") from failure
    count = locator.count()
    demand(count == 1, f"{where}: {description} matched {count} elements, it must match exactly one")
    return locator
