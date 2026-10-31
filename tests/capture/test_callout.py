from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

import pytest
from color_helpers import exact, marks_of
from helpers import ACCENT, Capture, figure, near
from shape_helpers import FILLED_URL, SENTENCE, TARGET_COLOR, TARGET_FRAME, URL, WHITE, callout, colors_in, on


def single(capture: Capture, *annotations: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return marks_of(capture.figures(figure(*annotations, url=extra.pop("url", URL), **extra)))[0]


def apart(block: Mapping[str, float], other: Mapping[str, float]) -> bool:
    return (
        block["x"] + block["width"] <= other["x"]
        or other["x"] + other["width"] <= block["x"]
        or block["y"] + block["height"] <= other["y"]
        or other["y"] + other["height"] <= block["y"]
    )


def test_callout_wraps_a_sentence_into_a_filled_block(capture: Capture) -> None:
    mark = single(capture, callout())
    block = mark["rectangle"]
    assert len(mark["lines"]) >= 2
    assert " ".join(line["text"] for line in mark["lines"]) == SENTENCE
    assert block["width"] <= 280
    assert block["height"] == 20 * len(mark["lines"]) + 20
    image = capture.image("01-page.png")
    inside = (round(block["x"]) + 3, round(block["y"]) + 3)
    assert exact(image, inside, ACCENT)
    right, bottom = int(block["x"] + block["width"]), int(block["y"] + block["height"])
    assert WHITE in colors_in(image, (int(block["x"]) + 12, int(block["y"]) + 10, right - 12, bottom - 10))


def test_callout_has_a_white_halo_like_a_label(capture: Capture) -> None:
    block = single(capture, callout())["rectangle"]
    image = capture.image("01-page.png")
    middle = round(block["y"] + block["height"] / 2)
    assert near(image.getpixel((round(block["x"]) - 1, middle)), WHITE, 60)


def test_callout_default_side_is_the_first_that_fits_in_order(capture: Capture) -> None:
    assert single(capture, callout())["side"] == "left"


@pytest.mark.parametrize(
    ("page", "expected"),
    [
        ("left:0;top:300px;width:100px;height:40px", "right"),
        ("left:0;top:300px;width:1270px;height:40px", "above"),
        ("left:0;top:0;width:1270px;height:40px", "below"),
    ],
)
def test_callout_skips_sides_that_do_not_fit(capture: Capture, page: str, expected: str) -> None:
    url = "data:text/html," + quote(
        f"<!doctype html><style>body{{margin:0}}#a{{position:absolute;{page}}}</style><div id=a></div>"
    )
    annotation = callout("#a")
    assert single(capture, annotation, url=url, full_page=False)["side"] == expected


@pytest.mark.parametrize(
    ("side", "start", "end"),
    [
        ("left", ("right", 330), (496, 330)),
        ("right", ("left", 330), (704, 330)),
        ("above", (600, "bottom"), (600, 296)),
        ("below", (600, "top"), (600, 364)),
    ],
)
def test_callout_sits_on_the_chosen_side_with_a_leader_to_the_edge(
    capture: Capture, side: str, start: tuple[Any, Any], end: tuple[int, int]
) -> None:
    mark = single(capture, callout(side=side))
    block = mark["rectangle"]
    edges = {
        "left": block["x"],
        "right": block["x"] + block["width"],
        "top": block["y"],
        "bottom": block["y"] + block["height"],
    }
    assert mark["side"] == side
    assert apart(block, mark["element"])
    assert apart(block, TARGET_FRAME)
    assert mark["end"] == {"x": end[0], "y": end[1]}
    assert mark["start"] == {
        "x": edges.get(start[0], start[0]),
        "y": edges.get(start[1], start[1]),
    }
    image = capture.image("01-page.png")
    middle = (mark["start"]["x"] + mark["end"]["x"]) / 2, (mark["start"]["y"] + mark["end"]["y"]) / 2
    assert near(image.getpixel((round(middle[0]), round(middle[1]))), ACCENT)
    assert image.getpixel((600, 330)) == TARGET_COLOR
    assert image.getpixel((501, 301)) == TARGET_COLOR
    assert image.getpixel((698, 358)) == TARGET_COLOR


def test_callout_width_narrows_the_wrapping(capture: Capture) -> None:
    wide = single(capture, callout(width=500))
    narrow = single(capture, callout(width=140))
    assert narrow["rectangle"]["width"] <= 140
    assert len(narrow["lines"]) > len(wide["lines"])
    assert wide["rectangle"]["width"] > 280


def test_callout_keeps_a_written_line_break(capture: Capture) -> None:
    mark = single(capture, callout(text="First line\nSecond line", width=400))
    assert [line["text"] for line in mark["lines"]] == ["First line", "Second line"]


def test_callout_breaks_a_word_longer_than_the_width(capture: Capture) -> None:
    word = "x" * 120
    mark = single(capture, callout(text=word, width=120))
    assert "".join(line["text"] for line in mark["lines"]) == word
    assert mark["rectangle"]["width"] <= 120


def test_callout_shrinks_its_default_width_on_a_narrow_viewport(capture: Capture) -> None:
    url = "data:text/html," + quote(
        "<!doctype html><style>body{margin:0}#a{position:absolute;left:50px;top:300px;width:60px;height:30px}</style>"
        "<div id=a></div>"
    )
    mark = single(capture, callout("#a"), url=url, full_page=False, viewport={"width": 240, "height": 700})
    assert mark["rectangle"]["width"] <= 236
    assert mark["side"] == "above"


def test_callout_text_is_not_drawn_twice_as_a_label(capture: Capture) -> None:
    mark = single(capture, callout(text="Short text", side="right"))
    image = capture.image("01-page.png")
    block = mark["rectangle"]
    assert image.getpixel((round(block["x"]) + 20, round(block["y"]) - 20)) == WHITE


@pytest.mark.parametrize("side", ["left", "right", "above", "below", None])
def test_callout_that_fits_nowhere_fails_naming_the_anchor(capture: Capture, side: str | None) -> None:
    annotation = callout("#all", **({"side": side} if side else {}))
    message = capture.failure(figure(annotation, url=FILLED_URL, full_page=False))
    assert "callout does not fit" in message
    assert side or "any side" in message
    assert '"selector": "#all"' in message


def test_explicit_side_without_room_fails_rather_than_moving(capture: Capture) -> None:
    annotation = {"kind": "callout", "anchor": on("#first"), "text": SENTENCE, "side": "left"}
    message = capture.failure(figure(annotation, url=URL))
    assert "callout does not fit left of" in message
    assert '"selector": "#first"' in message


def test_callout_too_tall_for_the_page_fails(capture: Capture) -> None:
    message = capture.failure(figure(callout(text="word " * 3000), url=URL))
    assert "callout does not fit any side" in message


def test_number_sits_on_the_corner_of_the_block(capture: Capture) -> None:
    mark = single(capture, callout(number=1))
    block = mark["rectangle"]
    assert mark["badge"] == {"x": block["x"], "y": block["y"]}


def test_number_placed_over_the_anchor_fails(capture: Capture) -> None:
    annotation = callout(side="left", number=1, placement="right")
    assert "number of the callout covers" in capture.failure(figure(annotation, url=URL))


def test_inherited_inside_falls_back_to_the_corner(capture: Capture) -> None:
    mark = single(capture, callout(number=1), placement="inside")
    assert mark["badge"] == {"x": mark["rectangle"]["x"], "y": mark["rectangle"]["y"]}
