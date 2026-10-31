from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page

from capture.constants import FAILURES_NAME
from capture.model import CaptureFailure, Options


def failure_picture(page: Page, name: str, options: Options) -> Path | None:
    path = options.output / FAILURES_NAME / f"{name}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        page.screenshot(path=str(path), full_page=True, animations="disabled", timeout=options.timeout)
    except PlaywrightError:
        return None
    return path


def with_picture(message: str, page: Page, name: str, options: Options) -> str:
    picture = failure_picture(page, name, options)
    return f"{message} (page at failure: {picture})" if picture else message


@contextmanager
def picture_on_failure(page: Page, name: str, where: str, options: Options) -> Generator[None]:
    try:
        yield
    except CaptureFailure as failure:
        raise CaptureFailure(with_picture(str(failure), page, name, options)) from failure
    except PlaywrightError as failure:
        first_line = str(failure).splitlines()[0]
        raise CaptureFailure(with_picture(f"{where}: {first_line}", page, name, options)) from failure
