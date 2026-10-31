import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from helpers import Capture, account_login, figure
from internals import internal
from playwright.sync_api import sync_playwright


class RecordingContext:
    def __init__(self, landing: Path) -> None:
        self.landing: Path = landing
        self.modes: dict[str, int | None] = {}

    def storage_state(self, path: str) -> None:
        state = Path(path)
        self.modes = {"state": mode_of(state), "landing": mode_of(self.landing), "directory": mode_of(state.parent)}
        with state.open("w") as file:
            file.write("{}")


class FakePage:
    url: str = "http://example.test/secret-landing"


def mode_of(path: Path) -> int | None:
    return path.stat().st_mode & 0o777 if path.exists() else None


@pytest.fixture
def wide_umask() -> Iterator[None]:
    previous = os.umask(0)
    yield
    os.umask(previous)


@pytest.mark.usefixtures("wide_umask")
def test_new_files_are_private_when_written(tmp_path: Path) -> None:
    state = tmp_path / "state" / "user-1.json"
    context = RecordingContext(state.with_suffix(".landing"))
    internal("session").save_state(context, FakePage(), state)
    assert context.modes == {"state": 0o600, "landing": 0o600, "directory": 0o700}
    assert mode_of(state) == 0o600
    assert mode_of(context.landing) == 0o600
    assert context.landing.read_text() == FakePage.url


@pytest.mark.usefixtures("wide_umask")
def test_wide_files_of_an_earlier_run_are_narrowed_before_rewriting(tmp_path: Path) -> None:
    state = tmp_path / "user-1.json"
    landing = state.with_suffix(".landing")
    for path in (state, landing):
        path.write_text("old")
        path.chmod(0o666)
    context = RecordingContext(landing)
    internal("session").save_state(context, FakePage(), state)
    assert context.modes["state"] == 0o600
    assert context.modes["landing"] == 0o600
    assert mode_of(state) == 0o600
    assert landing.read_text() == FakePage.url


def test_playwright_keeps_the_mode_of_an_existing_file(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    state.touch(mode=0o600)
    state.chmod(0o600)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context()
        context.storage_state(path=str(state))
        browser.close()
    assert state.read_text().startswith("{")
    assert mode_of(state) == 0o600


@pytest.mark.parametrize("content", ["", "not json"], ids=["empty", "garbage"])
def test_unreadable_saved_session_logs_in_again(capture: Capture, content: str) -> None:
    login = account_login("a@example.com")
    capture.figures(figure(url="/account"), login=login)
    next(capture.state.glob("account-*.json")).write_text(content)
    capture.figures(figure(url="/account"), login=login)
    assert next(capture.state.glob("account-*.json")).read_text().startswith("{")


@pytest.mark.parametrize("content", [b"\xff\xfe", b""], ids=["not-utf8", "empty"])
def test_unreadable_landing_file_logs_in_again(capture: Capture, content: bytes) -> None:
    login = account_login("a@example.com")
    capture.figures(figure(url="/account"), login=login)
    next(capture.state.glob("account-*.landing")).write_bytes(content)
    capture.figures(figure(url="/account"), login=login)
    assert next(capture.state.glob("account-*.landing")).read_text().endswith("/account")
