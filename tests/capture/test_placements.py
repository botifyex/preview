import json
from typing import Any

import pytest
from helpers import ACCENT, Capture, box, figure, near


def test_badge_outside_leaves_the_corner_free(capture: Capture) -> None:
    annotation = {
        "kind": "badge",
        "anchor": {"selector": "#tight"},
        "number": 1,
        "placement": "left",
    }
    manifest = capture.figures(figure(annotation, url="extras.html"))
    center = manifest["figures"][0]["marks"][0]["badge"]
    assert center == {"x": 376, "y": 412}
    image = capture.image("01-page.png")
    assert near(image.getpixel((370, 412)), ACCENT)
    assert not near(image.getpixel((402, 402)), ACCENT)


@pytest.mark.parametrize(
    ("placement", "center"),
    [("corner", (396, 396)), ("right", (524, 412)), ("above", (450, 376)), ("below", (450, 448))],
)
def test_badge_placements(capture: Capture, placement: str, center: tuple[int, int]) -> None:
    annotation = {
        "kind": "badge",
        "anchor": {"selector": "#tight"},
        "number": 1,
        "placement": placement,
    }
    manifest = capture.figures(figure(annotation, url="extras.html"))
    badge = manifest["figures"][0]["marks"][0]["badge"]
    assert (badge["x"], badge["y"]) == center


def test_badge_placed_outside_the_page_fails(capture: Capture) -> None:
    annotation = {"kind": "badge", "anchor": {"selector": "header"}, "number": 1, "placement": "above"}
    assert "outside the page" in capture.failure(figure(annotation))


def test_unknown_placement_is_refused(capture: Capture) -> None:
    annotation = {"kind": "badge", "anchor": {"selector": "#save"}, "number": 1, "placement": "middle"}
    assert "placement" in capture.failure(figure(annotation))


ROOMY_CENTERS = {
    "top-left": (596, 96),
    "corner": (596, 96),
    "top-right": (804, 96),
    "bottom-left": (596, 204),
    "bottom-right": (804, 204),
    "inside": (614, 114),
}


def numbered(placement: str | None = None, kind: str = "badge", anchor: str = "#roomy") -> dict[str, Any]:
    mark: dict[str, Any] = {"kind": kind, "anchor": {"selector": anchor}, "number": 1}
    return mark | ({"placement": placement} if placement else {})


def badge_at(capture: Capture, center: tuple[int, int], name: str = "01-page.png") -> bool:
    return near(capture.image(name).getpixel((center[0] - 10, center[1])), ACCENT)


@pytest.mark.parametrize(("placement", "center"), ROOMY_CENTERS.items())
@pytest.mark.parametrize("kind", ["badge", "box"])
def test_number_sits_at_each_placement(capture: Capture, kind: str, placement: str, center: tuple[int, int]) -> None:
    manifest = capture.figures(figure(numbered(placement, kind), url="extras.html"))
    badge = manifest["figures"][0]["marks"][0]["badge"]
    assert (badge["x"], badge["y"]) == center
    assert badge_at(capture, center)
    if kind == "badge":
        for other in set(ROOMY_CENTERS.values()) - {center}:
            assert not badge_at(capture, other), other


def test_inside_keeps_the_whole_number_in_the_shape(capture: Capture) -> None:
    capture.figures(figure(numbered("inside"), url="extras.html"))
    image = capture.image("01-page.png")
    for x in range(590, 600):
        assert not near(image.getpixel((x, 114)), ACCENT)
    for y in range(90, 100):
        assert not near(image.getpixel((614, y)), ACCENT)


def test_inside_too_small_for_the_number_fails(capture: Capture) -> None:
    message = capture.failure(figure(numbered("inside", anchor="#tight"), url="extras.html"))
    assert "too small" in message


def test_placement_without_a_number_is_not_checked(capture: Capture) -> None:
    capture.figures(figure(box("#tight"), url="extras.html", placement="inside"))


@pytest.mark.parametrize(
    ("spec_level", "figure_level", "annotation_level", "expected"),
    [
        (None, None, None, "corner"),
        ("top-right", None, None, "top-right"),
        ("top-right", "bottom-left", None, "bottom-left"),
        ("top-right", "bottom-left", "inside", "inside"),
        (None, "bottom-right", None, "bottom-right"),
    ],
)
def test_default_chain(
    capture: Capture, spec_level: str | None, figure_level: str | None, annotation_level: str | None, expected: str
) -> None:
    levels = {"placement": figure_level} if figure_level else {}
    extra = {"placement": spec_level} if spec_level else {}
    manifest = capture.figures(figure(numbered(annotation_level), url="extras.html", **levels), **extra)
    center = ROOMY_CENTERS[expected]
    badge = manifest["figures"][0]["marks"][0]["badge"]
    assert (badge["x"], badge["y"]) == center
    assert badge_at(capture, center)


def test_before_marks_inherit_the_figure_placement(capture: Capture, site: str) -> None:
    annotation = {"kind": "box", "anchor": {"selector": "#legacy"}, "number": 1}
    manifest = capture.figures(
        figure(url="index.html", before_url=f"{site}old.html", before_annotations=[annotation], placement="top-right")
    )
    badge = manifest["figures"][0]["marks"][0]["badge"]
    assert (badge["x"], badge["y"]) == (344, 496)


@pytest.mark.parametrize(
    ("build", "level"),
    [
        (lambda: {"figures": [figure()], "placement": "middle"}, "spec:"),
        (lambda: {"figures": [figure(placement="middle")]}, "figure 1"),
        (lambda: {"figures": [figure(numbered("middle"))]}, "annotation 1"),
    ],
    ids=["spec", "figure", "annotation"],
)
def test_invalid_placement_names_its_level(capture: Capture, build: Any, level: str) -> None:
    process = capture.run(build())
    assert process.returncode == 1
    assert level in process.stderr
    assert "placement" in process.stderr


@pytest.mark.parametrize("placement", ["inside", "top-right", "bottom-left", "bottom-right"])
def test_explicit_arrow_placement_that_makes_no_sense_fails(capture: Capture, placement: str) -> None:
    assert "does not apply to an arrow" in capture.failure(figure(numbered(placement, "arrow")))


@pytest.mark.parametrize("placement", ["corner", "top-left"])
def test_arrow_number_sits_on_its_tail(capture: Capture, placement: str) -> None:
    annotation = numbered(placement, "arrow", "#save") | {"offset": {"x": -180, "y": 0}}
    badge = capture.figures(figure(annotation))["figures"][0]["marks"][0]["badge"]
    assert badge == {"x": 200, "y": 224}


def test_inherited_placement_an_arrow_cannot_use_falls_back_to_its_tail(capture: Capture) -> None:
    annotation = numbered(None, "arrow", "#save") | {"offset": {"x": -180, "y": 0}}
    badge = capture.figures(figure(annotation, placement="inside"))["figures"][0]["marks"][0]["badge"]
    assert badge == {"x": 200, "y": 224}


def test_arrow_keeps_outside_placements(capture: Capture) -> None:
    annotation = numbered("right", "arrow", "#save") | {"offset": {"x": -180, "y": 0}}
    badge = capture.figures(figure(annotation))["figures"][0]["marks"][0]["badge"]
    assert badge == {"x": 484, "y": 224}


def test_explicit_corner_renders_exactly_like_the_default(capture: Capture) -> None:
    capture.figures(
        figure(numbered(), url="extras.html", slug="plain"), figure(numbered("corner"), url="extras.html", slug="named")
    )
    assert capture.image("01-plain.png").tobytes() == capture.image("02-named.png").tobytes()


def test_saved_spec_keeps_placement_fields_as_given(capture: Capture) -> None:
    capture.figures(figure(numbered(), url="extras.html", placement="inside"), placement="top-right")
    saved = json.loads((capture.out / "figures" / "spec.json").read_text())
    assert saved["placement"] == "top-right"
    assert saved["figures"][0]["placement"] == "inside"
    assert "placement" not in saved["figures"][0]["annotations"][0]
