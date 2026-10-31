import itertools
from collections.abc import Iterator
from dataclasses import dataclass

from capture.model import Box
from capture.scheme.constants import (
    ARROW_ROOM,
    LANE_OFFSETS,
    PANEL_CLEARANCE,
    PORT_CLEARANCE,
    ROUTE_SPACING,
    STUB_ROOM,
)
from capture.scheme.layout import Sheet

type Point = tuple[float, float]
type Route = list[Point]
type Segment = tuple[Point, Point]
type Direction = tuple[int, int]

LEFT: Direction = (-1, 0)
RIGHT: Direction = (1, 0)
UP: Direction = (0, -1)
DOWN: Direction = (0, 1)
DIRECTIONS = (RIGHT, DOWN, LEFT, UP)
SPOTS = (0.5, 0.3, 0.7)


@dataclass(frozen=True)
class Port:
    point: Point
    direction: Direction


@dataclass(frozen=True)
class Request:
    source: Box
    target: Box
    start: Point | None = None


def is_horizontal(direction: Direction) -> bool:
    return direction[1] == 0


def span(frame: Box, side_is_horizontal: bool) -> tuple[float, float]:
    return (frame.y, frame.bottom) if side_is_horizontal else (frame.x, frame.right)


def spots(frame: Box, side_is_horizontal: bool, other: tuple[float, float]) -> list[float]:
    low, high = span(frame, side_is_horizontal)
    shared_low, shared_high = max(low, other[0]), min(high, other[1])
    shared = [(shared_low + shared_high) / 2] if shared_low <= shared_high else []
    return [*shared, *(low + (high - low) * spot for spot in SPOTS)]


def edge_point(frame: Box, side: Direction, spot: float) -> Point:
    if is_horizontal(side):
        return (frame.right + PORT_CLEARANCE if side == RIGHT else frame.x - PORT_CLEARANCE, spot)
    return (spot, frame.bottom + PORT_CLEARANCE if side == DOWN else frame.y - PORT_CLEARANCE)


def facing(side: Direction) -> Direction:
    return (-side[0], -side[1])


def other_span(other: Box | Point, side_is_horizontal: bool) -> tuple[float, float]:
    if isinstance(other, Box):
        return span(other, side_is_horizontal)
    coordinate = other[1] if side_is_horizontal else other[0]
    return (coordinate, coordinate)


def exits(request: Request) -> Iterator[Port]:
    if request.start is not None:
        yield from (Port(request.start, direction) for direction in DIRECTIONS)
        return
    for side in DIRECTIONS:
        other = other_span(request.target, is_horizontal(side))
        for spot in spots(request.source, is_horizontal(side), other):
            yield Port(edge_point(request.source, side, spot), side)


def entries(request: Request) -> Iterator[Port]:
    towards = request.start if request.start is not None else request.source
    for side in DIRECTIONS:
        other = other_span(towards, is_horizontal(side))
        for spot in spots(request.target, is_horizontal(side), other):
            yield Port(edge_point(request.target, side, spot), facing(side))


def lanes(positions: list[float]) -> list[float]:
    return [position + offset for position in positions for offset in LANE_OFFSETS]


def paths(start: Port, end: Port, sheet: Sheet) -> Iterator[Route]:
    (start_x, start_y), (end_x, end_y) = start.point, end.point
    across = is_horizontal(start.direction)
    if across != is_horizontal(end.direction):
        corner = (end_x, start_y) if across else (start_x, end_y)
        yield [start.point, corner, end.point]
    elif (start_y if across else start_x) == (end_y if across else end_x):
        yield [start.point, end.point]
    elif across:
        for lane in lanes(sheet.vertical):
            yield [start.point, (lane, start_y), (lane, end_y), end.point]
    else:
        for lane in lanes(sheet.horizontal):
            yield [start.point, (start_x, lane), (end_x, lane), end.point]


def heading(segment: Segment) -> Direction:
    (first_x, first_y), (second_x, second_y) = segment
    delta_x, delta_y = second_x - first_x, second_y - first_y
    return ((delta_x > 0) - (delta_x < 0), (delta_y > 0) - (delta_y < 0))


def length(segment: Segment) -> float:
    (first_x, first_y), (second_x, second_y) = segment
    return abs(second_x - first_x) + abs(second_y - first_y)


def segments(route: Route) -> list[Segment]:
    return list(itertools.pairwise(route))


def segment_box(segment: Segment) -> Box:
    (first_x, first_y), (second_x, second_y) = segment
    return Box(min(first_x, second_x), min(first_y, second_y), abs(second_x - first_x), abs(second_y - first_y))


def overlaps(first: Box, second: Box, clearance: float) -> bool:
    return (
        first.x < second.right + clearance
        and second.x < first.right + clearance
        and first.y < second.bottom + clearance
        and second.y < first.bottom + clearance
    )


def shaped(route: Route, start: Port, end: Port) -> bool:
    parts = segments(route)
    return (
        all(first != second for first, second in parts)
        and heading(parts[0]) == start.direction
        and heading(parts[-1]) == end.direction
        and length(parts[-1]) >= ARROW_ROOM
        and length(parts[0]) >= STUB_ROOM
    )


def blocked(route: Route, request: Request, frames: list[Box]) -> bool:
    for index, segment in enumerate(segments(route)):
        box = segment_box(segment)
        for frame in frames:
            leaving = index == 0 and request.start is not None and frame == request.source
            if not leaving and overlaps(box, frame, PANEL_CLEARANCE):
                return True
    return False


def parallel(first: Segment, second: Segment) -> bool:
    return is_horizontal(heading(first)) == is_horizontal(heading(second))


def crowded(route: Route, taken: list[Route]) -> bool:
    return any(
        parallel(mine, theirs) and overlaps(segment_box(mine), segment_box(theirs), ROUTE_SPACING)
        for other in taken
        for mine in segments(route)
        for theirs in segments(other)
    )


def crosses(first: Segment, second: Segment) -> bool:
    return not parallel(first, second) and overlaps(segment_box(first), segment_box(second), 0)


def cost(route: Route, taken: list[Route]) -> tuple[int, int, float]:
    crossings = sum(crosses(mine, theirs) for other in taken for mine in segments(route) for theirs in segments(other))
    return (crossings, len(route), sum(length(segment) for segment in segments(route)))


def candidates(request: Request, sheet: Sheet, frames: list[Box], taken: list[Route]) -> Iterator[Route]:
    arrivals = list(entries(request))
    for start in exits(request):
        for end in arrivals:
            for route in paths(start, end, sheet):
                if shaped(route, start, end) and not blocked(route, request, frames) and not crowded(route, taken):
                    yield route


def routed(request: Request, sheet: Sheet, taken: list[Route]) -> Route | None:
    frames = [place.frame for place in sheet.places]
    return min(candidates(request, sheet, frames, taken), key=lambda route: cost(route, taken), default=None)
