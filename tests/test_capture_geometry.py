from capture_support import ACCENT, REMOVED, SAVE, Capture, box, figure, near


def test_box_geometry_matches_element_in_manifest_and_pixels(capture: Capture) -> None:
    manifest = capture.figures(figure(box("#save")))
    mark = manifest["figures"][0]["marks"][0]
    assert mark["element"] == SAVE
    image = capture.image("01-page.png")
    left, top, right, bottom = 296, 196, 464, 252
    middle_x, middle_y = (left + right) // 2, (top + bottom) // 2
    for point in [(left, middle_y), (right, middle_y), (middle_x, top), (middle_x, bottom)]:
        assert near(image.getpixel(point), ACCENT), point
    for point in [(left - 10, middle_y), (right + 10, middle_y), (middle_x, top - 10), (middle_x, bottom + 10)]:
        assert not near(image.getpixel(point), ACCENT), point


def test_page_without_marks_has_no_accent(capture: Capture) -> None:
    capture.figures(figure())
    image = capture.image("01-page.png")
    assert not near(image.getpixel((296, 224)), ACCENT)


def test_box_on_element_far_below_is_drawn_at_document_position(capture: Capture) -> None:
    manifest = capture.figures(figure(box("#far")))
    assert manifest["figures"][0]["marks"][0]["element"]["y"] == 2000
    image = capture.image("01-page.png")
    assert image.height >= 2060
    assert near(image.getpixel((96, 2030)), ACCENT)


def test_viewport_figure_on_a_scrolled_page_keeps_geometry(capture: Capture) -> None:
    manifest = capture.figures(figure(box("#far"), full_page=False))
    assert manifest["figures"][0]["marks"][0]["element"]["y"] == 2000
    image = capture.image("01-page.png")
    assert image.height == 800
    assert any(near(image.getpixel((96, y)), ACCENT) for y in range(800))


def test_retina_scale_keeps_geometry(capture: Capture) -> None:
    capture.figures(figure(box("#save"), viewport={"width": 1280, "height": 800, "scale": 2}))
    image = capture.image("01-page.png")
    assert image.width == 2560
    assert near(image.getpixel((296 * 2, 224 * 2)), ACCENT)


def test_inner_panel_is_scrolled_to_the_anchor(capture: Capture) -> None:
    manifest = capture.figures(figure(box("#panel-item")))
    element = manifest["figures"][0]["marks"][0]["element"]
    assert 400 <= element["y"] and element["y"] + element["height"] <= 500  # noqa: SIM300


def test_viewport_figure_refuses_anchor_outside_the_viewport(capture: Capture) -> None:
    message = capture.failure(figure(box("#save"), box("#far"), full_page=False))
    assert "outside the viewport" in message


def test_overlay_follows_a_positioned_root_element(capture: Capture) -> None:
    manifest = capture.figures(figure(box("#target"), url="shifted.html"))
    element = manifest["figures"][0]["marks"][0]["element"]
    assert (element["x"], element["y"]) == (150, 130)
    image = capture.image("01-page.png")
    assert near(image.getpixel((146, 150)), ACCENT)


def test_label_wider_than_the_page_fails(capture: Capture) -> None:
    annotation = {"kind": "label", "anchor": {"selector": "#save"}, "text": "very long words " * 40}
    assert "wider than the page" in capture.failure(figure(annotation))


def test_every_kind_draws_its_colour(capture: Capture) -> None:
    capture.figures(
        figure(
            {"kind": "arrow", "anchor": {"selector": "#save"}, "offset": {"x": -180, "y": 0}},
            {"kind": "badge", "anchor": {"selector": "#save"}, "number": 1},
            {"kind": "label", "anchor": {"selector": "#save"}, "text": "New"},
        ),
        figure(
            {"kind": "removed", "anchor": {"selector": "#block"}, "offset": {"y": 100}, "text": "Was here"},
            slug="gone",
        ),
    )
    arrow_image = capture.image("01-page.png")
    assert near(arrow_image.getpixel((230, 224)), ACCENT)
    gone = capture.image("02-gone.png")
    edge = [gone.getpixel((x, 596)) for x in range(96, 346)]
    painted = [near(pixel, REMOVED) for pixel in edge]
    assert any(painted) and not all(painted), "removed edge must be dashed"


def test_arrow_tip_touches_the_target_box(capture: Capture) -> None:
    manifest = capture.figures(
        figure({"kind": "arrow", "anchor": {"selector": "#save"}, "offset": {"x": -180, "y": 0}})
    )
    mark = manifest["figures"][0]["marks"][0]
    assert mark["tip"] == {"x": 296, "y": 224}
    assert mark["tail"] == {"x": 200, "y": 224}


def test_arrow_starting_inside_its_target_fails(capture: Capture) -> None:
    annotation = {"kind": "arrow", "anchor": {"selector": "#save"}, "offset": {"x": 5, "y": 0}}
    assert "inside its target" in capture.failure(figure(annotation))


def test_removed_marker_requires_an_offset_from_its_anchor(capture: Capture) -> None:
    annotation = {"kind": "removed", "anchor": {"selector": "#block"}}
    assert "offset" in capture.failure(figure(annotation))


def test_removed_marker_outside_the_page_fails(capture: Capture) -> None:
    annotation = {"kind": "removed", "anchor": {"selector": "#block"}, "offset": {"x": -5000}}
    assert "outside the page" in capture.failure(figure(annotation))


def test_before_url_produces_its_own_preceding_number(capture: Capture, site: str) -> None:
    manifest = capture.figures(
        figure(
            box("#block"),
            before_url=f"{site}old.html",
            before_annotations=[box("#legacy")],
        )
    )
    entries = manifest["figures"]
    assert [(entry["file"], entry["role"]) for entry in entries] == [
        ("figures/01-page-before.png", "before"),
        ("figures/02-page.png", "current"),
    ]
    assert entries[0]["marks"][0]["element"] == {"x": 100, "y": 500, "width": 240, "height": 80}


def test_overlay_does_not_widen_or_lengthen_the_page(capture: Capture) -> None:
    first = capture.figures(figure(slug="plain"))["figures"][0]["page"]
    image = capture.image("01-plain.png")
    assert (image.width, image.height) == (first["width"], first["height"])
    capture.figures(figure(box("#far"), slug="marked"))
    marked = capture.image("01-marked.png")
    assert (marked.width, marked.height) == (image.width, image.height)


def test_too_many_marks_warn(capture: Capture) -> None:
    annotations = [box("#save") for _ in range(6)]
    process = capture.run({"figures": [figure(*annotations)]})
    assert process.returncode == 0, process.stderr
    assert "6 marks" in process.stderr
