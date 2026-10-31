import hashlib
import json
import os
from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Page
from playwright.sync_api import Error as PlaywrightError

from capture.constants import IDENTITY_LENGTH
from capture.failures import picture_on_failure
from capture.locators import single_visible
from capture.model import CaptureFailure, Options, Spec
from capture.steps import open_url, run_steps


def locale_option(spec: Spec) -> Spec:
    return {"locale": spec["locale"]} if "locale" in spec else {}


def login_identity(spec: Spec) -> str:
    login = spec["login"]
    resolved = [os.environ.get(step["value_env"]) for step in login["steps"] if "value_env" in step]
    text = json.dumps([spec["base_url"], login, resolved], sort_keys=True)
    return hashlib.sha256(text.encode()).hexdigest()[:IDENTITY_LENGTH]


def state_path(spec: Spec, options: Options) -> Path:
    return options.state_directory / f"{spec['login']['name']}-{login_identity(spec)}.json"


def landing_path(state: Path) -> Path:
    return state.with_suffix(".landing")


def prepare_state_directory(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    ignore = directory / ".gitignore"
    if not ignore.exists():
        ignore.write_text("*\n")


def save_state(context: BrowserContext, page: Page, path: Path) -> None:
    prepare_state_directory(path.parent)
    context.storage_state(path=str(path))
    path.chmod(0o600)
    landing = landing_path(path)
    landing.write_text(page.url)
    landing.chmod(0o600)


def log_in(browser: Browser, spec: Spec, options: Options, path: Path) -> None:
    login = spec["login"]
    context = browser.new_context(ignore_https_errors=options.ignore_https, **locale_option(spec))
    try:
        page = context.new_page()
        with picture_on_failure(page, "login", "login", options):
            run_steps(page, login["steps"], spec["base_url"], "login", options.timeout)
            single_visible(page, login["expect"], "login expect", options.timeout)
            save_state(context, page, path)
    finally:
        context.close()


def session_alive(browser: Browser, spec: Spec, options: Options, path: Path) -> bool:
    landing = landing_path(path)
    if not path.exists() or not landing.exists():
        return False
    try:
        context = browser.new_context(
            ignore_https_errors=options.ignore_https, storage_state=str(path), **locale_option(spec)
        )
    except PlaywrightError:
        return False
    try:
        page = context.new_page()
        open_url(page, landing.read_text(), options.timeout)
        single_visible(page, spec["login"]["expect"], "login expect", options.timeout)
        return True
    except (CaptureFailure, PlaywrightError):
        return False
    finally:
        context.close()


def ensure_login(browser: Browser, spec: Spec, options: Options, fresh: bool) -> Path:
    path = state_path(spec, options)
    if fresh or not session_alive(browser, spec, options, path):
        log_in(browser, spec, options, path)
    return path
