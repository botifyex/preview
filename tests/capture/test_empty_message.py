from pathlib import Path

import pytest
from internals import internal
from playwright.sync_api import Error as PlaywrightError

MESSAGES = ["", "\n", "   \n  "]


class MessagePage:
    def __init__(self, message: str) -> None:
        self.message: str = message

    def wait_for_timeout(self, _milliseconds: int) -> None:
        raise PlaywrightError(self.message)

    def screenshot(self, **_: object) -> None:
        raise PlaywrightError("no picture")


@pytest.mark.parametrize("message", MESSAGES)
def test_run_steps_survives_an_empty_message(message: str) -> None:
    step = {"action": "wait", "milliseconds": 1}
    with pytest.raises(internal("model").CaptureFailure, match=r"figure step 1 \(wait\): .*failed"):
        internal("steps").run_steps(MessagePage(message), [step], "http://example.test/", "figure", 100)


@pytest.mark.parametrize("message", MESSAGES)
def test_picture_on_failure_survives_an_empty_message(tmp_path: Path, message: str) -> None:
    model = internal("model")
    options = model.Options(tmp_path, tmp_path, False, False, 100)
    with (
        pytest.raises(model.CaptureFailure, match=r"figure: .*failed"),
        internal("failures").picture_on_failure(MessagePage(""), "name", "figure", options),
    ):
        raise PlaywrightError(message)


def test_first_line_of_a_longer_message_is_kept() -> None:
    step = {"action": "wait", "milliseconds": 1}
    with pytest.raises(internal("model").CaptureFailure) as caught:
        internal("steps").run_steps(MessagePage("first\nsecond"), [step], "http://example.test/", "figure", 100)
    assert str(caught.value) == "figure step 1 (wait): first"
