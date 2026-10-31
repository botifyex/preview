from typing import Any

import pytest
from internals import internal

constants = internal("scheme.constants")
layout = internal("scheme.layout")
routing = internal("scheme.routing")
placement = internal("scheme.placement")
model = internal("model")
Size, Slot = layout.Size, layout.Slot
Box = model.Box
Request = routing.Request


def slots(count: int, width: float = 200, height: float = 100, heading: float = 0) -> list[Any]:
    return [Slot(Size(width, height), heading) for _ in range(count)]


def test_scale_goes_down_only() -> None:
    assert layout.fitted(Size(1000, 500), 500) == Size(500, 250)
    assert layout.fitted(Size(300, 200), 500) == Size(300, 200)


@pytest.mark.parametrize(("name", "expected"), [("row", 5), ("column", 1), ("grid", 2)])
def test_column_count(name: str, expected: int) -> None:
    assert layout.column_count(name, 2, 5) == expected


def test_grid_columns_never_exceed_the_panels() -> None:
    assert layout.column_count("grid", 9, 2) == 2


def test_row_places_panels_side_by_side() -> None:
    sheet = layout.arranged(slots(3), 3, 10, 20)
    assert [place.image.x for place in sheet.places] == [20, 230, 440]
    assert {place.image.y for place in sheet.places} == {20}
    assert sheet.size == Size(660, 140)


def test_column_centres_narrow_panels() -> None:
    wide, narrow = Slot(Size(400, 100), 0), Slot(Size(200, 100), 0)
    sheet = layout.arranged([wide, narrow], 1, 10, 20)
    assert sheet.places[0].image.center[0] == sheet.places[1].image.center[0]
    assert sheet.places[1].image.y == 130


def test_grid_rows_take_the_tallest_panel() -> None:
    tall, short = Slot(Size(100, 300), 0), Slot(Size(100, 100), 0)
    sheet = layout.arranged([short, tall, short], 2, 10, 0)
    assert sheet.places[2].image.y == 310


def test_a_heading_widens_its_frame_and_takes_a_band() -> None:
    sheet = layout.arranged([Slot(Size(100, 100), 300)], 1, 10, 0)
    place = sheet.places[0]
    assert place.frame == Box(0, 0, 300, 100 + constants.HEADING_BAND)
    assert place.image == Box(100, constants.HEADING_BAND, 100, 100)


def test_images_of_a_row_stay_aligned_when_one_has_no_heading() -> None:
    sheet = layout.arranged([Slot(Size(100, 100), 50), Slot(Size(100, 100), 0)], 2, 10, 0)
    assert sheet.places[0].image.y == sheet.places[1].image.y
    assert sheet.places[1].frame.y == sheet.places[1].image.y


def test_oversize_is_refused_in_image_pixels() -> None:
    layout.refuse_oversize(Size(8000, 10), 1, "here")
    with pytest.raises(model.CaptureFailure, match="here: scheme is 8002x20 px"):
        layout.refuse_oversize(Size(4001, 10), 2, "here")


def request_between(sheet: Any, source: int, target: int, start: tuple[float, float] | None = None) -> Any:
    places = sheet.places
    return Request(places[source].frame, places[target].frame, start)


def assert_clear(route: list[Any], sheet: Any, exempt: Any = None) -> None:
    for index, segment in enumerate(routing.segments(route)):
        for place in sheet.places:
            if not (index == 0 and place.frame == exempt):
                assert not routing.overlaps(routing.segment_box(segment), place.frame, 0)


def test_neighbours_in_a_row_get_a_straight_arrow() -> None:
    sheet = layout.arranged(slots(2), 2, 72, 48)
    route = routing.routed(request_between(sheet, 0, 1), sheet, [])
    assert route == [(254, 98), (314, 98)]


def test_neighbours_in_a_column_get_a_straight_arrow() -> None:
    sheet = layout.arranged(slots(2), 1, 72, 48)
    route = routing.routed(request_between(sheet, 0, 1), sheet, [])
    assert route == [(148, 154), (148, 214)]


def test_skipping_a_panel_in_a_row_goes_around_it() -> None:
    sheet = layout.arranged(slots(3), 3, 72, 48)
    route = routing.routed(request_between(sheet, 0, 2), sheet, [])
    assert len(route) == 4
    assert_clear(route, sheet)


def test_a_diagonal_in_a_grid_stays_in_the_gaps() -> None:
    sheet = layout.arranged(slots(4), 2, 72, 48)
    route = routing.routed(request_between(sheet, 0, 3), sheet, [])
    assert_clear(route, sheet)


def test_a_centre_panel_without_gaps_cannot_be_routed() -> None:
    sheet = layout.arranged(slots(9), 3, 0, 48)
    assert routing.routed(request_between(sheet, 4, 0), sheet, []) is None


def test_a_second_link_keeps_away_from_the_first() -> None:
    sheet = layout.arranged(slots(2), 2, 72, 48)
    first = routing.routed(request_between(sheet, 0, 1), sheet, [])
    second = routing.routed(request_between(sheet, 1, 0), sheet, [first])
    assert not routing.crowded(second, [first])
    assert second[0][1] != first[0][1]


def test_a_mark_route_leaves_its_panel_and_crosses_no_other() -> None:
    sheet = layout.arranged(slots(3), 3, 72, 48)
    start = (100.0, 70.0)
    route = routing.routed(request_between(sheet, 0, 2, start), sheet, [])
    assert route[0] == start
    assert_clear(route, sheet, sheet.places[0].frame)


def test_marks_scale_into_the_composite() -> None:
    mark = {
        "number": 1,
        "text": "kept",
        "rectangle": {"x": 110, "y": 60, "width": 40, "height": 20},
        "badge": {"x": 110, "y": 60},
        "bottom": 80,
    }
    scaled = placement.scaled_mark(mark, Box(100, 50, 200, 100), Box(1000, 2000, 100, 50), 0.5)
    assert scaled["rectangle"] == {"x": 1005, "y": 2005, "width": 20, "height": 10}
    assert scaled["badge"] == {"x": 1005, "y": 2005}
    assert scaled["bottom"] == 2015
    assert scaled["text"] == "kept"


def test_a_label_avoids_panels_and_lines() -> None:
    size = Size(400, 200)
    route = [(100.0, 100.0), (300.0, 100.0)]
    free = placement.label_box(route, 40, [], [route], size)
    assert free.bottom <= 100
    upper = Box(0, 0, 400, 90)
    assert placement.label_box(route, 40, [upper], [route], size).y >= 100


def test_a_label_without_room_is_refused() -> None:
    route = [(100.0, 100.0), (300.0, 100.0)]
    assert placement.label_box(route, 40, [Box(0, 0, 400, 200)], [route], Size(400, 200)) is None
