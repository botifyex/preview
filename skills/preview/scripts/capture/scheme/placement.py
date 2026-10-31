from collections.abc import Iterator
from typing import Any, cast

from capture.model import Box, Spec
from capture.scheme.constants import LABEL_HEIGHT, LABEL_OFFSET, LABEL_PADDING, LABEL_SPOTS
from capture.scheme.layout import Size
from capture.scheme.routing import Route, Segment, heading, is_horizontal, length, overlaps, segment_box, segments


def scaled_y(value: float, shown: Box, image: Box, scale: float) -> float:
    return image.y + (value - shown.y) * scale


def scaled_point(value: Spec, shown: Box, image: Box, scale: float) -> Spec:
    result = {
        **value,
        "x": image.x + (value["x"] - shown.x) * scale,
        "y": scaled_y(value["y"], shown, image, scale),
    }
    for field in ("width", "height"):
        if field in value:
            result[field] = value[field] * scale
    return result


def scaled_value(key: str, value: Any, shown: Box, image: Box, scale: float) -> Any:
    if isinstance(value, dict):
        point = cast("Spec", value)
        return scaled_point(point, shown, image, scale) if "x" in point else point
    if isinstance(value, list):
        return [scaled_value(key, item, shown, image, scale) for item in cast("list[Any]", value)]
    return scaled_y(value, shown, image, scale) if key == "bottom" else value


def scaled_mark(mark: Spec, shown: Box, image: Box, scale: float) -> Spec:
    return {key: scaled_value(key, value, shown, image, scale) for key, value in mark.items()}


def beside_horizontal(left: float, y: float, width: float) -> list[Box]:
    return [
        Box(left, y - LABEL_OFFSET - LABEL_HEIGHT, width, LABEL_HEIGHT),
        Box(left, y + LABEL_OFFSET, width, LABEL_HEIGHT),
    ]


def beside_vertical(x: float, top: float, width: float) -> list[Box]:
    return [
        Box(x + LABEL_OFFSET, top, width, LABEL_HEIGHT),
        Box(x - LABEL_OFFSET - width, top, width, LABEL_HEIGHT),
    ]


def label_spots(segment: Segment, width: float) -> list[Box]:
    box = segment_box(segment)
    if is_horizontal(heading(segment)):
        lefts = [box.x + box.width * along - width / 2 for along in LABEL_SPOTS]
        return [spot for left in (*lefts, box.x, box.right - width) for spot in beside_horizontal(left, box.y, width)]
    tops = [box.y + box.height * along - LABEL_HEIGHT / 2 for along in LABEL_SPOTS]
    return [spot for top in (*tops, box.y, box.bottom - LABEL_HEIGHT) for spot in beside_vertical(box.x, top, width)]


def corner_spots(route: Route, width: float) -> Iterator[Box]:
    for x, y in route[1:-1]:
        yield Box(x - width / 2, y - LABEL_OFFSET - LABEL_HEIGHT, width, LABEL_HEIGHT)
        yield Box(x - width / 2, y + LABEL_OFFSET, width, LABEL_HEIGHT)


def label_box(route: Route, text_width: float, avoid: list[Box], routes: list[Route], size: Size) -> Box | None:
    width = text_width + 2 * LABEL_PADDING
    lines = [segment_box(segment) for other in routes for segment in segments(other)]
    along = [
        spot for segment in sorted(segments(route), key=length, reverse=True) for spot in label_spots(segment, width)
    ]
    for spot in [*along, *corner_spots(route, width)]:
        inside = spot.inside(0, 0, size.width, size.height)
        if inside and not any(overlaps(spot, other, 0) for other in [*avoid, *lines]):
            return spot
    return None
