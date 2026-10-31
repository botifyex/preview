from typing import Any

import pytest
from helpers import Capture, box, figure, near


def test_waits_for_animation_before_measuring(capture: Capture) -> None:
    manifest = capture.figures(figure(box("#slide")))
    assert manifest["figures"][0]["marks"][0]["element"]["x"] == 400


def test_endless_animation_does_not_hang_and_is_measured_at_rest(capture: Capture) -> None:
    manifest = capture.figures(figure(box("#spinner")))
    assert manifest["figures"][0]["marks"][0]["element"]["x"] == 700


def test_steps_reach_the_state_that_is_annotated(capture: Capture) -> None:
    steps = [
        {"action": "fill", "target": {"role": "textbox", "name": "Name"}, "value": "Test data"},
        {"action": "click", "target": {"selector": "#apply"}},
        {"action": "wait", "target": {"selector": "#late"}},
        {"action": "press", "key": "Tab"},
        {"action": "wait", "milliseconds": 10},
    ]
    manifest = capture.figures(figure(box("#late"), steps=steps))
    assert manifest["figures"][0]["marks"][0]["element"]["x"] == 640


def test_late_element_without_a_step_still_fails(capture: Capture) -> None:
    assert "#late" in capture.failure(figure(box("#late")))


def test_failing_step_names_its_position(capture: Capture) -> None:
    steps = [{"action": "click", "target": {"selector": "#missing"}}]
    assert "step 1 (click)" in capture.failure(figure(steps=steps))


def test_value_env_missing_fails_without_guessing(capture: Capture) -> None:
    steps = [{"action": "fill", "target": {"selector": "#name"}, "value_env": "PREVIEW_UNSET"}]
    assert "PREVIEW_UNSET" in capture.failure(figure(steps=steps))


def test_dark_theme_reaches_the_page(capture: Capture) -> None:
    capture.figures(figure(slug="light"), figure(slug="dark", theme="dark"))
    assert near(capture.image("01-light.png").getpixel((5, 700)), (246, 246, 246), 2)
    assert near(capture.image("02-dark.png").getpixel((5, 700)), (16, 16, 16), 2)


def test_hover_step_reaches_the_hover_state(capture: Capture) -> None:
    steps = [{"action": "hover", "target": {"selector": "#hover-target"}}]
    capture.figures(figure(box("#tip"), url="extras.html", steps=steps))


@pytest.mark.parametrize(
    ("field", "anchor"),
    [("has_touch", "#touch"), ("reduced_motion", "#reduced")],
)
def test_device_flags_reach_the_page(capture: Capture, field: str, anchor: str) -> None:
    assert anchor in capture.failure(figure(box(anchor), url="extras.html"))
    flag: dict[str, Any] = {field: True}
    capture.figures(figure(box(anchor), url="extras.html", **flag))


PORTAL_PIXEL = (20, 780)


def test_dev_overlay_in_a_shadow_root_shows_by_default(capture: Capture) -> None:
    capture.figures(figure(url="extras.html"))
    assert near(capture.image("01-page.png").getpixel(PORTAL_PIXEL), (255, 0, 0), 2)


@pytest.mark.parametrize("selector", ["nextjs-portal", "#shadow-inner"])
def test_hide_removes_overlay_host_or_shadow_content(capture: Capture, selector: str) -> None:
    capture.figures(figure(url="extras.html"), hide=[selector, "#not-on-this-page"])
    assert near(capture.image("01-page.png").getpixel(PORTAL_PIXEL), (255, 255, 255), 2)


def test_invalid_hide_is_refused(capture: Capture) -> None:
    assert "hide" in capture.failure(figure(), hide="nextjs-portal")
