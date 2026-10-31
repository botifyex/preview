from typing import Any

import pytest
from helpers import Capture, near
from internals import internal
from scheme_helpers import BLUE, BLUE_PIXEL, GREEN_PIXEL, YELLOW, YELLOW_PIXEL, center, panel, run_scheme, scheme
from scheme_shape_helpers import BLACK, DIMMED_BLUE, composite, cropped
from shape_helpers import blend

validation = internal("validation")
model = internal("model")

NAME = "01-scheme.png"
CARD = {"selector": "#card"}
PAST = "figure scheme panel 1: marks reach past the crop"
TOUCHING = "marks reach past the crop"


def spotlight(**extra: Any) -> dict[str, Any]:
    return {"kind": "spotlight", "anchor": CARD, **extra}


def on_card(padding: int, *annotations: dict[str, Any], shade: str = BLUE) -> dict[str, Any]:
    return panel(shade, crop=CARD, crop_padding=padding, annotations=list(annotations))


def connector(anchor: str, origin: str) -> dict[str, Any]:
    return {"kind": "connector", "anchor": {"selector": anchor}, "from": {"selector": origin}}


def test_cropped_spotlight_keeps_the_hole_clear_and_the_veil_on(capture: Capture) -> None:
    item = run_scheme(capture, scheme(on_card(60, spotlight())))["panels"][0]
    rectangle, mark = item["rectangle"], item["marks"][0]
    assert (rectangle["width"], rectangle["height"]) == (240, 180)
    image = capture.image(NAME)
    assert near(image.getpixel(center(mark["rectangle"])), GREEN_PIXEL, 0)
    x, y, right, bottom = (
        int(rectangle["x"]),
        int(rectangle["y"]),
        int(rectangle["x"] + rectangle["width"]),
        int(rectangle["y"] + rectangle["height"]),
    )
    for point in [(x + 4, y + 4), (right - 4, y + 4), (x + 4, bottom - 4), (right - 4, bottom - 4)]:
        assert near(image.getpixel(point), DIMMED_BLUE, 2), point
    assert near(image.getpixel((int(mark["rectangle"]["x"]) - 6, center(mark["rectangle"])[1])), DIMMED_BLUE, 2)


@pytest.mark.parametrize(
    ("padding", "extra"),
    [(16, {}), (24, {"number": 1}), (40, {"text": "Hi"}), (40, {"number": 1, "text": "Hi"})],
    ids=["hole", "number", "label", "number and label"],
)
def test_spotlight_that_fits_passes(capture: Capture, padding: int, extra: dict[str, Any]) -> None:
    run_scheme(capture, scheme(on_card(padding, spotlight(**extra))))
    assert (capture.out / "figures" / NAME).exists()


@pytest.mark.parametrize(
    ("padding", "extra"),
    [(2, {}), (14, {"number": 1}), (33, {"text": "Hi"})],
    ids=["hole", "number", "label"],
)
def test_spotlight_part_past_the_crop_is_refused(capture: Capture, padding: int, extra: dict[str, Any]) -> None:
    assert PAST in capture.failure(scheme(on_card(padding, spotlight(**extra))))


def test_other_marks_still_count_beside_a_spotlight(capture: Capture) -> None:
    other = {"kind": "box", "anchor": {"selector": "#corner"}}
    assert PAST in capture.failure(scheme(on_card(60, spotlight(), other)))


@pytest.mark.parametrize(
    ("anchor", "origin"),
    [("#target", "#beyond"), ("#beyond", "#target"), ("#target", "#beside"), ("#beside", "#target")],
    ids=["from far", "anchor far", "from just beside", "anchor just beside"],
)
def test_connector_with_an_end_outside_the_crop_is_refused(capture: Capture, anchor: str, origin: str) -> None:
    figure = composite(cropped(connector(anchor, origin)))
    assert TOUCHING in capture.failure(figure)


def test_connector_with_both_ends_shown_passes(capture: Capture) -> None:
    figure = composite(cropped(connector("#target", "#source")))
    assert capture.figures(figure)["figures"][0]["panels"][0]["marks"][0]["kind"] == "connector"


def test_each_panel_may_have_its_own_spotlight(capture: Capture) -> None:
    entry = run_scheme(capture, scheme(on_card(60, spotlight()), on_card(60, spotlight(), shade=YELLOW)))
    image = capture.image(NAME)
    tints = [blend(BLUE_PIXEL, BLACK, 0.6), blend(YELLOW_PIXEL, BLACK, 0.6)]
    for item, tint in zip(entry["panels"], tints, strict=True):
        rectangle = item["rectangle"]
        assert near(image.getpixel((int(rectangle["x"]) + 4, int(rectangle["y"]) + 4)), tint, 2)
        assert near(image.getpixel(center(item["marks"][0]["rectangle"])), GREEN_PIXEL, 0)


def test_two_spotlights_in_one_panel_are_refused_by_validation() -> None:
    figure = scheme(panel(annotations=[spotlight()]), panel(annotations=[spotlight(), spotlight()]))
    spec = {"environment": "test", "base_url": "http://localhost/", "figures": [figure]}
    with pytest.raises(model.CaptureFailure, match="panel 2: at most one spotlight per image, found 2"):
        validation.validate_spec(spec)


def test_two_spotlights_fail_before_the_browser(capture: Capture) -> None:
    capture.site = "http://127.0.0.1:9/"
    stderr = capture.failure(scheme(panel(annotations=[spotlight(), spotlight()])))
    assert stderr.startswith("error: figure 1 (scheme) panel 1: at most one spotlight per image, found 2")
    assert not capture.out.exists()
