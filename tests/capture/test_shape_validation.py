from typing import Any

import pytest
from helpers import Capture, figure
from shape_helpers import on

ANCHOR = on("#save")
FROM = on("#block")


def callout(**extra: Any) -> dict[str, Any]:
    return {"kind": "callout", "anchor": ANCHOR, "text": "Some words", **extra}


def connector(**extra: Any) -> dict[str, Any]:
    return {"kind": "connector", "anchor": ANCHOR, "from": FROM, **extra}


def plain(kind: str, **extra: Any) -> dict[str, Any]:
    return {"kind": kind, "anchor": ANCHOR, **extra}


REFUSED = {
    "callout-no-text": ({"kind": "callout", "anchor": ANCHOR}, "callout requires ['text']"),
    "callout-no-anchor": ({"kind": "callout", "text": "x"}, "callout requires ['anchor']"),
    "callout-text-type": (callout(text=5), "text must be a string"),
    "callout-text-blank": (callout(text="  \n "), "callout text must not be empty"),
    "callout-text-empty": (callout(text=""), "callout text must not be empty"),
    "callout-side-unknown": (callout(side="up"), "side must be one of"),
    "callout-side-type": (callout(side=1), "side must be one of"),
    "callout-width-zero": (callout(width=0), "width must be a number from 80"),
    "callout-width-small": (callout(width=79), "width must be a number from 80"),
    "callout-width-negative": (callout(width=-200), "width must be a number from 80"),
    "callout-width-text": (callout(width="200"), "width must be a number from 80"),
    "callout-width-bool": (callout(width=True), "width must be a number from 80"),
    "callout-width-huge": (callout(width=10**10), "width must be a number from 80"),
    "callout-inside": (callout(placement="inside"), "placement inside does not apply to a callout"),
    "connector-no-from": (plain("connector"), "connector requires ['from']"),
    "connector-no-anchor": ({"kind": "connector", "from": FROM}, "connector requires ['anchor']"),
    "connector-from-type": (connector(**{"from": "#block"}), "target must be an object"),
    "connector-from-empty": (connector(**{"from": {}}), "exactly one of selector"),
    "connector-heads-unknown": (connector(heads="start"), "heads must be one of"),
    "connector-heads-type": (connector(heads=True), "heads must be one of"),
    "connector-inside": (connector(placement="inside"), "placement inside does not apply to a connector"),
    "connector-top-right": (connector(placement="top-right"), "does not apply to a connector"),
    "side-on-box": (plain("box", side="left"), "side applies only to a callout"),
    "width-on-ellipse": (plain("ellipse", width=100), "width applies only to a callout"),
    "heads-on-arrow": (plain("arrow", heads="end"), "heads applies only to a connector"),
    "heads-on-underline": (plain("underline", heads="end"), "heads applies only to a connector"),
    "ellipse-no-anchor": ({"kind": "ellipse"}, "ellipse requires ['anchor']"),
    "underline-no-anchor": ({"kind": "underline"}, "underline requires ['anchor']"),
    "highlight-no-anchor": ({"kind": "highlight"}, "highlight requires ['anchor']"),
    "spotlight-no-anchor": ({"kind": "spotlight"}, "spotlight requires ['anchor']"),
    "ellipse-number": (plain("ellipse", number=1.5), "number must be an integer"),
    "underline-text": (plain("underline", text=1), "text must be a string"),
    "highlight-color": (plain("highlight", color="red"), "color must be #RRGGBB"),
    "spotlight-placement": (plain("spotlight", placement="nowhere"), "placement must be one of"),
}


@pytest.mark.parametrize(("annotation", "expected"), REFUSED.values(), ids=REFUSED.keys())
def test_bad_shape_fields_are_refused_before_the_browser(
    capture: Capture, annotation: dict[str, Any], expected: str
) -> None:
    unreachable = figure(annotation, url="http://127.0.0.1:9/never")
    message = capture.failure(unreachable)
    assert message.startswith("error: ")
    assert expected in message
    assert "page at failure" not in message


def test_second_spotlight_in_one_image_is_refused(capture: Capture) -> None:
    message = capture.failure(figure(plain("spotlight"), plain("spotlight"), url="http://127.0.0.1:9/never"))
    assert message.startswith("error: ")
    assert "at most one spotlight per image, found 2" in message


def test_second_spotlight_in_before_annotations_is_refused(capture: Capture) -> None:
    annotations = [plain("spotlight"), plain("spotlight")]
    spec = figure(before_url="http://127.0.0.1:9/old", before_annotations=annotations, url="http://127.0.0.1:9/never")
    assert "before: at most one spotlight" in capture.failure(spec)


def test_one_spotlight_in_each_image_of_a_pair_is_allowed(capture: Capture, site: str) -> None:
    spotlight = {"kind": "spotlight", "anchor": on("#block")}
    legacy = {"kind": "spotlight", "anchor": on("#legacy")}
    capture.figures(figure(spotlight, before_url=f"{site}old.html", before_annotations=[legacy]))
    assert capture.image("01-page-before.png").width == 1280
