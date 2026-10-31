from collections.abc import Iterator
from pathlib import Path

import pytest
from helpers import Capture, account_login, box, figure


def blocked(process_stderr: str, returncode: int) -> None:
    assert returncode == 1
    assert process_stderr.startswith("error: "), process_stderr
    assert "Traceback" not in process_stderr


@pytest.fixture
def read_only(tmp_path: Path) -> Iterator[Path]:
    directory = tmp_path / "locked"
    directory.mkdir(mode=0o500)
    yield directory
    directory.chmod(0o700)


def test_out_under_a_file(capture: Capture) -> None:
    blocker = capture.directory / "blocker"
    blocker.write_text("mine")
    capture.out = blocker / "out"
    process = capture.run({"figures": [figure()]})
    blocked(process.stderr, process.returncode)
    assert blocker.read_text() == "mine"


def test_out_in_a_read_only_directory(capture: Capture, read_only: Path) -> None:
    capture.out = read_only / "out"
    process = capture.run({"figures": [figure()]})
    blocked(process.stderr, process.returncode)


def test_state_directory_under_a_file(capture: Capture) -> None:
    blocker = capture.directory / "blocker"
    blocker.write_text("mine")
    capture.state = blocker / "state"
    process = capture.run({"figures": [figure(url="/account")], "login": account_login("a@example.com")})
    blocked(process.stderr, process.returncode)


def test_state_directory_taken_by_a_file(capture: Capture) -> None:
    capture.state.write_text("mine")
    process = capture.run({"figures": [figure(url="/account")], "login": account_login("a@example.com")})
    blocked(process.stderr, process.returncode)
    assert capture.state.read_text() == "mine"


def test_read_only_state_directory(capture: Capture, read_only: Path) -> None:
    capture.state = read_only
    process = capture.run({"figures": [figure(url="/account")], "login": account_login("a@example.com")})
    blocked(process.stderr, process.returncode)


def test_failure_picture_directory_blocked_keeps_the_real_failure(capture: Capture) -> None:
    capture.out.mkdir()
    (capture.out / "failures").write_text("mine")
    process = capture.run({"figures": [figure(box("#missing"))]})
    blocked(process.stderr, process.returncode)
    assert "matched no visible element" in process.stderr
    assert (capture.out / "failures").read_text() == "mine"
