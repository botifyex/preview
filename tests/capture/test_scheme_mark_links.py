from typing import Any

import pytest
from helpers import ACCENT, Capture, near
from scheme_helpers import panel
from scheme_shape_helpers import NEW_KINDS, SINGLE_FIGURE, annotation, center_of, composite, cropped

LINK = {"from": "source", "to": "target", "from_mark": 1}
ALONG = 16


def linked(capture: Capture, kind: str) -> tuple[dict[str, Any], dict[str, Any]]:
    figure = composite(panel(), cropped(annotation(kind), id="source"), panel(id="target"), links=[LINK])
    entry = capture.figures(figure)["figures"][0]
    return entry["panels"][1]["marks"][0], entry["links"][0]


def toward(first: dict[str, float], second: dict[str, float], distance: float) -> tuple[int, int]:
    span = max(abs(second["x"] - first["x"]), abs(second["y"] - first["y"]))
    share = distance / span
    return (
        round(first["x"] + (second["x"] - first["x"]) * share),
        round(first["y"] + (second["y"] - first["y"]) * share),
    )


def expected_number(mark: dict[str, Any]) -> tuple[float, float]:
    if mark["kind"] == "connector":
        first, second = center_of(mark["element"]), center_of(mark["source"])
        return ((first[0] + second[0]) / 2, (first[1] + second[1]) / 2)
    return (mark["rectangle"]["x"], mark["rectangle"]["y"])


def test_connector_number_lies_on_its_line_between_the_ends(capture: Capture) -> None:
    mark, _ = linked(capture, "connector")
    assert mark["start"]["x"] < mark["badge"]["x"] < mark["end"]["x"]
    assert mark["badge"]["y"] == pytest.approx(mark["start"]["y"]) == pytest.approx(mark["end"]["y"])


def test_callout_number_sits_on_its_block(capture: Capture) -> None:
    mark, _ = linked(capture, "callout")
    block = mark["rectangle"]
    assert block["x"] <= mark["badge"]["x"] < block["x"] + block["width"]
    assert block["y"] <= mark["badge"]["y"] < block["y"] + block["height"]


@pytest.mark.parametrize("kind", NEW_KINDS)
def test_link_starts_at_the_number_of_the_mark(capture: Capture, kind: str) -> None:
    mark, link = linked(capture, kind)
    badge = mark["badge"]
    assert link["tail"] == {"x": badge["x"], "y": badge["y"]}
    assert (badge["x"], badge["y"]) == pytest.approx(expected_number(mark))
    image = capture.image(SINGLE_FIGURE)
    assert near(image.getpixel((round(badge["x"]) - 7, round(badge["y"]))), ACCENT)
    first, second = link["points"][:2]
    assert near(image.getpixel(toward(first, second, ALONG)), ACCENT)
    assert first == {"x": badge["x"], "y": badge["y"]}
