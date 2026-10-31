from typing import Any

import pytest
from helpers import Capture, figure

PAGE = "hidden.html"
SEND_TOP = 100


def hidden_page(*annotations: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return figure(*annotations, url=PAGE, **extra)


@pytest.mark.parametrize(
    "anchor",
    [
        {"selector": ".send"},
        {"text": "Send"},
        {"text": "^Se.d$", "match": "regex"},
        {"text": "send", "match": "substring"},
        {"role": "button", "name": "Send"},
    ],
    ids=["selector", "text", "regex", "substring", "role"],
)
def test_anchor_takes_the_one_visible_match(capture: Capture, anchor: dict[str, Any]) -> None:
    manifest = capture.figures(hidden_page({"kind": "box", "anchor": anchor}))
    assert manifest["figures"][0]["marks"][0]["element"]["y"] == SEND_TOP


@pytest.mark.parametrize("action", ["click", "hover", "wait"])
def test_step_acts_on_the_one_visible_match(capture: Capture, action: str) -> None:
    step = {"action": action, "target": {"selector": ".send"}}
    capture.figures(hidden_page(steps=[step]))


def test_click_reaches_the_visible_element(capture: Capture) -> None:
    step = {"action": "click", "target": {"text": "Send"}}
    capture.figures(hidden_page({"kind": "box", "anchor": {"text": "Clicked"}}, steps=[step]))


@pytest.mark.parametrize("action", ["fill", "press"])
def test_typing_reaches_the_visible_element(capture: Capture, action: str) -> None:
    target = {"selector": ".note"}
    steps = {"fill": {"value": "x"}, "press": {"key": "x"}}[action]
    step = {"action": action, "target": target, **steps}
    capture.figures(hidden_page({"kind": "box", "anchor": {"text": "Typed"}}, steps=[step]))


@pytest.mark.parametrize(
    "anchor",
    [{"selector": ".pair"}, {"text": "Pair"}, {"role": "link", "name": "Pair"}],
    ids=["selector", "text", "role"],
)
def test_several_visible_matches_still_fail(capture: Capture, anchor: dict[str, Any]) -> None:
    assert "matched 2 elements" in capture.failure(hidden_page({"kind": "box", "anchor": anchor}))


def test_only_hidden_matches_fail(capture: Capture) -> None:
    message = capture.failure(hidden_page({"kind": "box", "anchor": {"selector": ".ghost"}}))
    assert "matched no visible element" in message


def test_crop_takes_the_one_visible_match(capture: Capture) -> None:
    panel = {"url": PAGE, "crop": {"selector": ".send"}}
    capture.figures({"slug": "scheme", "panels": [panel]})
