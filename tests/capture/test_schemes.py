from itertools import pairwise
from typing import Any

import pytest
from helpers import ACCENT, Capture, account_login, figure, near
from scheme_helpers import (
    BACKGROUND_PIXEL,
    BLUE_PIXEL,
    CYAN,
    GREEN_PIXEL,
    VIEWPORT,
    YELLOW,
    YELLOW_PIXEL,
    center,
    has_color,
    inner_pixel,
    panel,
    run_scheme,
    scheme,
    three,
)

NAME = "01-scheme.png"
FULL = 640
BOX = {"kind": "box", "anchor": {"selector": "#card"}, "number": 2}


def test_row_makes_one_numbered_picture(capture: Capture) -> None:
    entry = run_scheme(capture, three())
    assert entry["file"] == f"figures/{NAME}"
    assert (entry["number"], entry["slug"], entry["role"], entry["layout"]) == (1, "scheme", "scheme", "row")
    tops = {item["rectangle"]["y"] for item in entry["panels"]}
    lefts = [item["rectangle"]["x"] for item in entry["panels"]]
    assert len(tops) == 1
    assert lefts == sorted(set(lefts))
    assert sorted(path.name for path in (capture.out / "figures").iterdir()) == [NAME, "manifest.json", "spec.json"]
    assert near(inner_pixel(capture, NAME, entry["panels"][0]["rectangle"]), BLUE_PIXEL, 2)
    assert near(inner_pixel(capture, NAME, entry["panels"][1]["rectangle"]), YELLOW_PIXEL, 2)
    assert near(capture.image(NAME).getpixel((5, 5)), BACKGROUND_PIXEL, 2)
    assert capture.image(NAME).size == (entry["viewport"]["width"], entry["viewport"]["height"])


def test_column_stacks_panels(capture: Capture) -> None:
    entry = run_scheme(capture, three(layout="column"))
    rectangles = [item["rectangle"] for item in entry["panels"]]
    assert len({rectangle["x"] for rectangle in rectangles}) == 1
    assert rectangles[0]["y"] + rectangles[0]["height"] < rectangles[1]["y"]
    assert near(inner_pixel(capture, NAME, rectangles[1]), YELLOW_PIXEL, 2)


def test_grid_wraps_at_its_columns(capture: Capture) -> None:
    entry = run_scheme(capture, scheme(panel(), panel(YELLOW), panel(CYAN), layout="grid", columns=2))
    first, second, third = [item["rectangle"] for item in entry["panels"]]
    assert first["y"] == second["y"] < third["y"]
    assert first["x"] == third["x"] < second["x"]
    assert entry["layout"] == "grid"


def test_panel_width_scales_down_and_marks_follow(capture: Capture) -> None:
    entry = run_scheme(capture, scheme(panel(annotations=[BOX]), panel_width=200))
    item = entry["panels"][0]
    assert item["scale"] == 0.5
    assert (item["rectangle"]["width"], item["rectangle"]["height"]) == (200, 150)
    element = item["marks"][0]["element"]
    assert element == {
        "x": item["rectangle"]["x"] + 50,
        "y": item["rectangle"]["y"] + 40,
        "width": 60,
        "height": 30,
    }
    assert near(capture.image(NAME).getpixel(center(element)), GREEN_PIXEL, 10)
    assert entry["viewport"]["scale"] == 1


def test_panel_width_never_scales_up(capture: Capture) -> None:
    item = run_scheme(capture, scheme(panel(), panel_width=2000))["panels"][0]
    assert item["scale"] == 1
    assert item["rectangle"]["width"] == VIEWPORT["width"]


def test_crop_keeps_only_the_element_and_padding(capture: Capture) -> None:
    item = run_scheme(capture, scheme(panel(crop={"selector": "#card"}, crop_padding=10)))["panels"][0]
    rectangle = item["rectangle"]
    assert (rectangle["width"], rectangle["height"]) == (140, 80)
    assert near(capture.image(NAME).getpixel(center(rectangle)), GREEN_PIXEL, 2)
    assert near(capture.image(NAME).getpixel((int(rectangle["x"]) + 3, int(rectangle["y"]) + 3)), BLUE_PIXEL, 2)


def test_crop_padding_defaults_to_sixteen(capture: Capture) -> None:
    rectangle = run_scheme(capture, scheme(panel(crop={"selector": "#card"})))["panels"][0]["rectangle"]
    assert (rectangle["width"], rectangle["height"]) == (152, 92)


def test_crop_shifts_marks(capture: Capture) -> None:
    cropped = panel(crop={"selector": "#card"}, crop_padding=40, annotations=[BOX])
    item = run_scheme(capture, scheme(cropped))["panels"][0]
    assert item["marks"][0]["element"]["x"] == item["rectangle"]["x"] + 40
    assert item["marks"][0]["element"]["y"] == item["rectangle"]["y"] + 40


def test_a_mark_past_the_crop_is_refused(capture: Capture) -> None:
    stderr = capture.failure(scheme(panel(crop={"selector": "#card"}, annotations=[BOX])))
    assert "figure scheme panel 1: marks reach past the crop" in stderr


def test_crop_outside_the_viewport_is_refused(capture: Capture) -> None:
    small = {"width": 100, "height": 50, "scale": 1}
    stderr = capture.failure(scheme(panel(crop={"selector": "#card"}, viewport=small)))
    assert "figure scheme panel 1: crop falls outside the picture" in stderr


def test_titles_draw_above_the_panel(capture: Capture) -> None:
    item = run_scheme(capture, scheme(panel(title="Open the page")))["panels"][0]
    rectangle = item["rectangle"]
    assert item["title"] == "Open the page"
    band = (int(rectangle["x"]), int(rectangle["y"]) - 30, int(rectangle["x"]) + 100, int(rectangle["y"]) - 5)
    assert has_color(capture, NAME, band, (29, 41, 57))
    assert not has_color(capture, NAME, band, ACCENT)


def test_step_numbers_draw_without_a_title_too(capture: Capture) -> None:
    entry = run_scheme(capture, scheme(panel(title="First"), panel(), steps_numbers=True, color="#E6004C"))
    for item in entry["panels"]:
        rectangle = item["rectangle"]
        band = (int(rectangle["x"]), int(rectangle["y"]) - 30, int(rectangle["x"]) + 26, int(rectangle["y"]) - 5)
        assert has_color(capture, NAME, band, ACCENT)


def test_a_title_wider_than_its_panel_widens_the_frame(capture: Capture) -> None:
    crop = {"selector": "#card"}
    long = "A long title that is much wider than the small cropped element below it"
    entry = run_scheme(capture, scheme(panel(crop=crop, title=long), panel(crop=crop, title="Short")))
    first, second = [item["rectangle"] for item in entry["panels"]]
    assert second["x"] > first["x"] + first["width"] + 150


def test_background_and_gap_are_honoured(capture: Capture) -> None:
    entry = run_scheme(capture, scheme(panel(), panel(YELLOW), gap=100, background="#102030"))
    first, second = [item["rectangle"] for item in entry["panels"]]
    assert second["x"] - first["x"] - first["width"] == 100
    assert near(capture.image(NAME).getpixel((5, 5)), (16, 32, 48), 2)


def test_edge_to_edge_arrow_with_text(capture: Capture) -> None:
    linked = scheme(panel(id="a"), panel(YELLOW, id="b"), links=[{"from": "a", "to": "b", "text": "next"}])
    entry = run_scheme(capture, linked)
    first, second = [item["rectangle"] for item in entry["panels"]]
    link = entry["links"][0]
    assert first["x"] + first["width"] < link["tail"]["x"] < link["tip"]["x"] < second["x"]
    assert link["tail"]["y"] == link["tip"]["y"]
    assert (link["from"], link["to"], link["style"], link["text"]) == ("a", "b", "solid", "next")
    middle = int((link["tail"]["x"] + link["tip"]["x"]) / 2), int(link["tail"]["y"])
    assert near(capture.image(NAME).getpixel(middle), ACCENT)
    label = link["label"]
    assert near(capture.image(NAME).getpixel((int(label["x"]) + 3, int(label["y"]) + 12)), ACCENT)
    assert label["x"] >= first["x"] + first["width"]
    assert label["x"] + label["width"] <= second["x"]


def test_long_text_widens_the_default_gap(capture: Capture) -> None:
    text = "goes on to the next page of the path"
    entry = run_scheme(capture, scheme(panel(), panel(YELLOW), links=[{"from": 1, "to": 2, "text": text}]))
    first, second = [item["rectangle"] for item in entry["panels"]]
    label = entry["links"][0]["label"]
    assert second["x"] - first["x"] - first["width"] > label["width"]


def test_text_that_cannot_fit_is_refused(capture: Capture) -> None:
    text = "goes on to the next page of the path"
    links = [{"from": 1, "to": 2, "text": text}]
    stderr = capture.failure(scheme(panel(), panel(YELLOW), links=links, gap=30, panel_width=150))
    assert "figure scheme link 1: text does not fit beside the arrow" in stderr


def test_dashed_differs_from_solid(capture: Capture) -> None:
    linked = scheme(panel(), panel(YELLOW), links=[{"from": 1, "to": 2, "style": "dashed"}], gap=200)
    link = run_scheme(capture, linked)["links"][0]
    y = int(link["tail"]["y"])
    line = [capture.image(NAME).getpixel((x, y)) for x in range(int(link["tail"]["x"]) + 4, int(link["tip"]["x"]) - 24)]
    assert link["style"] == "dashed"
    assert any(near(pixel, ACCENT) for pixel in line)
    assert not all(near(pixel, ACCENT) for pixel in line)


def test_solid_is_unbroken(capture: Capture) -> None:
    linked = scheme(panel(), panel(YELLOW), links=[{"from": 1, "to": 2}], gap=200)
    link = run_scheme(capture, linked)["links"][0]
    y = int(link["tail"]["y"])
    line = [capture.image(NAME).getpixel((x, y)) for x in range(int(link["tail"]["x"]) + 4, int(link["tip"]["x"]) - 24)]
    assert all(near(pixel, ACCENT) for pixel in line)


@pytest.mark.parametrize("layout", ["row", "column"])
def test_sequence_links_each_panel_to_the_next(capture: Capture, layout: str) -> None:
    entry = run_scheme(capture, three(layout=layout, links="sequence"))
    assert [(link["from"], link["to"]) for link in entry["links"]] == [(1, 2), (2, 3)]
    for link in entry["links"]:
        assert len(link["points"]) == 2
        middle = int((link["tail"]["x"] + link["tip"]["x"]) / 2), int((link["tail"]["y"] + link["tip"]["y"]) / 2)
        assert near(capture.image(NAME).getpixel(middle), ACCENT)


def crossing(entry: dict[str, Any], link: dict[str, Any]) -> bool:
    for first, second in pairwise(link["points"]):
        left, right = sorted((first["x"], second["x"]))
        top, bottom = sorted((first["y"], second["y"]))
        for item in entry["panels"]:
            box = item["rectangle"]
            if (
                left < box["x"] + box["width"]
                and box["x"] < right + 1
                and top < box["y"] + box["height"]
                and box["y"] < bottom + 1
            ):
                return True
    return False


def test_links_in_a_grid_do_not_cross_panels(capture: Capture) -> None:
    links = [{"from": 1, "to": 4}, {"from": 2, "to": 3}, {"from": 1, "to": 2}, {"from": 2, "to": 1, "style": "dashed"}]
    grid = scheme(panel(), panel(YELLOW), panel(CYAN), panel(), layout="grid", columns=2, links=links, panel_width=200)
    entry = run_scheme(capture, grid)
    assert len(entry["links"]) == 4
    assert not any(crossing(entry, link) for link in entry["links"])


def test_skipping_a_panel_in_a_row_does_not_cross_it(capture: Capture) -> None:
    entry = run_scheme(capture, three(links=[{"from": 1, "to": 3}]))
    link = entry["links"][0]
    assert not crossing(entry, link)
    assert len(link["points"]) == 4


def test_a_link_with_no_route_is_refused(capture: Capture) -> None:
    small = {"width": 100, "height": 60, "scale": 1}
    panels = [panel(viewport=small) for _ in range(9)]
    links = [{"from": 5, "to": 1}]
    stderr = capture.failure(scheme(*panels, layout="grid", columns=3, gap=0, links=links))
    assert "figure scheme link 1: cannot route 5 to 1 without crossing a panel" in stderr


def test_from_mark_starts_at_the_mark(capture: Capture) -> None:
    linked = scheme(
        panel(id="source", annotations=[BOX]),
        panel(YELLOW, id="target"),
        panel_width=200,
        links=[{"from": "source", "to": "target", "from_mark": 2}],
    )
    entry = run_scheme(capture, linked)
    link = entry["links"][0]
    badge = entry["panels"][0]["marks"][0]["badge"]
    assert link["from_mark"] == 2
    assert link["tail"] == {"x": badge["x"], "y": badge["y"]}
    target = entry["panels"][1]["rectangle"]
    assert link["tip"]["x"] < target["x"]
    assert not crossing({"panels": entry["panels"][1:]}, link)
    assert has_color(
        capture, NAME, (int(badge["x"]) - 8, int(badge["y"]) - 8, int(badge["x"]) + 8, int(badge["y"]) + 8), ACCENT
    )
    first = entry["panels"][0]["rectangle"]
    after = int(first["x"] + first["width"]) + 2
    assert near(capture.image(NAME).getpixel((after, int(link["tail"]["y"]))), ACCENT)


def test_login_in_a_panel_next_to_a_signed_out_one(capture: Capture) -> None:
    signed_in = {
        "url": "/account",
        "annotations": [{"kind": "box", "anchor": {"selector": "#user"}, "number": 1}],
    }
    signed_out = {
        "url": "/account",
        "login": False,
        "annotations": [{"kind": "box", "anchor": {"selector": "#signin"}, "number": 1}],
    }
    entry = run_scheme(capture, scheme(signed_in, signed_out), login=account_login("panel@example.com"))
    assert [len(item["marks"]) for item in entry["panels"]] == [1, 1]
    assert entry["panels"][0]["url"].endswith("/account")
    assert list(capture.state.glob("account-*.json"))


def test_figure_login_false_keeps_every_panel_signed_out(capture: Capture) -> None:
    signed_out = {"url": "/account", "annotations": [{"kind": "box", "anchor": {"selector": "#signin"}}]}
    capture.figures(scheme(signed_out, login=False), login=account_login("nobody@example.com"))
    assert not list(capture.state.glob("account-*.json"))


def test_full_page_panel_shows_the_whole_page(capture: Capture) -> None:
    deep = {
        "url": "scheme.html?deep#ccccff",
        "full_page": True,
        "annotations": [{"kind": "box", "anchor": {"selector": "#deep"}}],
    }
    item = run_scheme(capture, scheme(deep, panel_width=400))["panels"][0]
    assert item["rectangle"]["height"] > 1000
    assert item["marks"][0]["element"]["y"] == item["rectangle"]["y"] + 1000


def test_full_page_is_off_by_default(capture: Capture) -> None:
    deep = {"url": "scheme.html?deep#ccccff"}
    item = run_scheme(capture, scheme(deep))["panels"][0]
    assert item["rectangle"]["height"] == VIEWPORT["height"]


def test_panel_inherits_placement_and_color(capture: Capture) -> None:
    box = {"kind": "box", "anchor": {"selector": "#card"}, "number": 1}
    entry = run_scheme(capture, scheme(panel(annotations=[box]), color="#0055AA", placement="inside"))
    mark = entry["panels"][0]["marks"][0]
    rectangle = mark["rectangle"]
    assert mark["color"] == "#0055AA"
    assert rectangle["x"] < mark["badge"]["x"] < rectangle["x"] + rectangle["width"]


def test_high_density_panels_set_the_picture_scale(capture: Capture) -> None:
    double = {"width": 400, "height": 300, "scale": 2}
    entry = run_scheme(capture, scheme(panel(viewport=double)))
    assert entry["viewport"]["scale"] == 2
    assert capture.image(NAME).size == (2 * entry["viewport"]["width"], 2 * entry["viewport"]["height"])
    assert entry["panels"][0]["rectangle"]["width"] == 400


def test_too_large_a_picture_is_refused(capture: Capture) -> None:
    wide = {"width": 4000, "height": 100, "scale": 1}
    panels = [panel(viewport=wide) for _ in range(3)]
    stderr = capture.failure(scheme(*panels, panel_width=FULL * 6))
    assert "figure scheme: scheme is" in stderr
    assert "over the limit of 8000 a side" in stderr


def test_many_panels_warn(capture: Capture) -> None:
    small = {"width": 100, "height": 60, "scale": 1}
    process = capture.run({"figures": [scheme(*[panel(viewport=small) for _ in range(7)])]})
    assert process.returncode == 0, process.stderr
    assert "warning: figures/01-scheme.png: 7 panels, keep one idea per image" in process.stderr


def test_six_panels_do_not_warn(capture: Capture) -> None:
    small = {"width": 100, "height": 60, "scale": 1}
    process = capture.run({"figures": [scheme(*[panel(viewport=small) for _ in range(6)])]})
    assert process.returncode == 0, process.stderr
    assert "warning" not in process.stderr


def test_an_ordinary_figure_keeps_its_entry_shape(capture: Capture) -> None:
    entry = capture.figures(figure())["figures"][0]
    assert set(entry) == {"number", "file", "slug", "role", "url", "viewport", "theme", "page", "marks", "warnings"}
