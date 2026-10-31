from typing import Any

import pytest
from helpers import Capture, account_login, near
from internals import internal
from playwright.sync_api import sync_playwright
from scheme_helpers import GREEN_PIXEL, run_scheme, scheme
from shape_helpers import WHITE

validation = internal("validation")
model = internal("model")
page_scripts = internal("page_scripts")

NAME = "01-scheme.png"
EMPTY_PIXEL = (170, 0, 0)
ADD = {"action": "click", "target": {"selector": "#add"}}
GO = {"action": "click", "target": {"selector": "#go"}}
CHECK = {"action": "click", "target": {"selector": "#check"}}
BOX = {"kind": "box", "anchor": {"selector": "#add"}, "number": 1}
SPOTLIGHT = {"kind": "spotlight", "anchor": {"selector": "#add"}}


def path(*panels: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return scheme(*panels, continuous=True, **extra)


def shop(*steps: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {"url": "shop.html", "steps": list(steps), **extra}


def pixel_in(capture: Capture, item: dict[str, Any], x: float, y: float) -> tuple[int, ...]:
    rectangle = item["rectangle"]
    return capture.image(NAME).getpixel((round(rectangle["x"] + x), round(rectangle["y"] + y)))  # pyright: ignore[reportReturnType]


def state_pixel(capture: Capture, item: dict[str, Any]) -> tuple[int, ...]:
    return pixel_in(capture, item, 140, 80)


def test_cart_is_carried_across_panels(capture: Capture) -> None:
    entry = run_scheme(capture, path(shop(ADD), {"url": "cart.html"}, links="sequence"))
    assert entry["continuous"] is True
    assert near(state_pixel(capture, entry["panels"][1]), GREEN_PIXEL, 2)


def test_without_continuous_each_panel_starts_fresh(capture: Capture) -> None:
    entry = run_scheme(capture, scheme(shop(ADD), {"url": "cart.html"}, links="sequence"))
    assert entry["continuous"] is False
    assert near(state_pixel(capture, entry["panels"][1]), EMPTY_PIXEL, 2)


def test_panel_without_url_stays_and_records_where_it_ended(capture: Capture) -> None:
    entry = run_scheme(capture, path(shop(ADD), {"steps": [GO]}, {}))
    first, second, third = entry["panels"]
    assert first["url"].endswith("/shop.html")
    assert second["url"].endswith("/cart.html")
    assert third["url"].endswith("/cart.html")
    assert near(state_pixel(capture, third), GREEN_PIXEL, 2)


def test_url_on_a_later_panel_navigates(capture: Capture) -> None:
    entry = run_scheme(capture, path({"url": "cart.html"}, {"url": "shop.html"}))
    assert entry["panels"][1]["url"].endswith("/shop.html")


def picture_of(capture: Capture, item: dict[str, Any]) -> bytes:
    rectangle = item["rectangle"]
    left, top = round(rectangle["x"]), round(rectangle["y"])
    area = (left, top, left + round(rectangle["width"]), top + round(rectangle["height"]))
    return capture.image(NAME).crop(area).tobytes()


@pytest.mark.parametrize("mark", [BOX, SPOTLIGHT], ids=["box", "spotlight"])
def test_marks_do_not_reach_the_next_panel(capture: Capture, mark: dict[str, Any]) -> None:
    entry = run_scheme(capture, path(shop(annotations=[mark]), {}, shop()))
    marked, stayed, clean = entry["panels"]
    assert stayed["marks"] == []
    assert picture_of(capture, marked) != picture_of(capture, clean)
    assert picture_of(capture, stayed) == picture_of(capture, clean)


def test_next_panel_clicks_under_the_marks_of_the_last(capture: Capture) -> None:
    entry = run_scheme(capture, path(shop(annotations=[SPOTLIGHT, BOX]), {"steps": [ADD]}))
    assert near(pixel_in(capture, entry["panels"][1], 260, 60), GREEN_PIXEL, 2)


def test_overlay_never_takes_a_click() -> None:
    marks = [
        {
            "kind": "spotlight",
            "color": "#E6004C",
            "number": None,
            "text": None,
            "rectangle": {"x": 300, "y": 300, "width": 10, "height": 10},
            "opacity": 0.6,
            "veil": {"width": 800, "height": 600},
        }
    ]
    area = {"x": 0, "y": 0, "width": 800, "height": 600}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_content("<button onclick=\"this.textContent='done'\">go</button>")
        page.evaluate(
            page_scripts.DRAW_SCRIPT,
            {"marks": marks, "page": {"width": 800, "height": 600}, "area": area, "radius": 14},
        )
        assert page.locator('svg[data-preview="overlay"]').count() == 1
        page.locator("button").click(timeout=2000)
        assert page.locator("button").text_content() == "done"
        browser.close()


def test_hide_is_undone_before_the_next_steps_and_kept_in_the_picture(capture: Capture) -> None:
    entry = run_scheme(capture, path(shop(), {"steps": [CHECK]}), hide=["#banner"])
    first, second = entry["panels"]
    for item in (first, second):
        assert near(pixel_in(capture, item, 140, 220), WHITE, 2)
    assert near(pixel_in(capture, second, 260, 60), GREEN_PIXEL, 2)


def test_login_works_as_for_a_figure(capture: Capture) -> None:
    box = {"kind": "box", "anchor": {"selector": "#user"}}
    entry = run_scheme(
        capture,
        path({"url": "/account", "annotations": [box]}, {"annotations": [box]}),
        login=account_login("path@example.com"),
    )
    assert [len(item["marks"]) for item in entry["panels"]] == [1, 1]
    assert list(capture.state.glob("account-*.json"))


def test_figure_login_false_stays_signed_out(capture: Capture) -> None:
    box = {"kind": "box", "anchor": {"selector": "#signin"}}
    panels = path({"url": "/account", "annotations": [box]}, login=False)
    capture.figures(panels, login=account_login("nobody@example.com"))
    assert not list(capture.state.glob("account-*.json"))


def test_failure_names_the_panel(capture: Capture) -> None:
    stderr = capture.failure(path(shop(), {"steps": [{"action": "click", "target": {"selector": "#ghost"}}]}))
    assert "figure scheme panel 2 step 1" in stderr
    assert (capture.out / "failures" / "scheme-panel-2.png").exists()


def test_figure_settings_reach_the_shared_page(capture: Capture) -> None:
    entry = run_scheme(capture, path(shop(), {}, viewport={"width": 500, "height": 300, "scale": 2}))
    assert entry["viewport"]["scale"] == 2
    assert entry["panels"][1]["rectangle"]["width"] == 500


CASES: list[tuple[dict[str, Any], str]] = [
    (path({"steps": []}, {"url": "a"}), "panel 1: url is required"),
    (scheme({"url": "a"}, {}), "panel 2: url is required"),
    (path({"url": "a"}, {"url": 5}), "panel 2: url must be a valid address"),
    (path({"url": "a"}, {"viewport": {"width": 400}}), "panel 2: viewport does not apply with continuous"),
    (path({"url": "a", "theme": "dark"}), "panel 1: theme does not apply with continuous"),
    (path({"url": "a", "has_touch": True}), "panel 1: has_touch does not apply with continuous"),
    (path({"url": "a", "reduced_motion": True}), "panel 1: reduced_motion does not apply with continuous"),
    (path({"url": "a", "login": False}), "panel 1: login does not apply with continuous"),
    (scheme({"url": "a"}, continuous="yes"), "continuous must be true or false"),
    (scheme({"url": "a", "continuous": True}), "panel 1: continuous does not apply to a panel"),
]


@pytest.mark.parametrize(("figure", "message"), CASES, ids=[message for _, message in CASES])
def test_a_bad_path_is_refused(figure: dict[str, Any], message: str) -> None:
    spec = {"environment": "test", "base_url": "http://localhost/", "figures": [figure]}
    with pytest.raises(model.CaptureFailure, match=message):
        validation.validate_spec(spec)


def test_refusal_comes_before_the_browser(capture: Capture) -> None:
    capture.site = "http://127.0.0.1:9/"
    stderr = capture.failure(path({"url": "a", "theme": "dark"}))
    assert stderr.startswith("error: figure 1 (scheme) panel 1: theme does not apply with continuous")
    assert not capture.out.exists()
