from dataclasses import dataclass
from math import ceil

from capture.model import Box, demand
from capture.scheme.constants import HEADING_BAND, SIDE_LIMIT


@dataclass(frozen=True)
class Size:
    width: float
    height: float


@dataclass(frozen=True)
class Slot:
    image: Size
    heading: float


@dataclass(frozen=True)
class Place:
    image: Box
    frame: Box


@dataclass(frozen=True)
class Sheet:
    size: Size
    places: list[Place]
    vertical: list[float]
    horizontal: list[float]


def fit_scale(source: Size, panel_width: float) -> float:
    return min(1.0, panel_width / source.width)


def fitted(source: Size, panel_width: float) -> Size:
    scale = fit_scale(source, panel_width)
    return Size(source.width * scale, source.height * scale)


def column_count(layout: str, columns: int, count: int) -> int:
    return {"row": count, "column": 1}.get(layout, min(columns, count))


def frame_width(slot: Slot) -> float:
    return max(slot.image.width, slot.heading)


def starts(extents: list[float], gap: float, margin: float) -> list[float]:
    return [margin + gap * index + sum(extents[:index]) for index in range(len(extents))]


def channels(begins: list[float], extents: list[float], margin: float) -> list[float]:
    ends = [begin + extent for begin, extent in zip(begins, extents, strict=True)]
    between = [(end + begin) / 2 for end, begin in zip(ends, begins[1:], strict=False)]
    return [margin / 2, *between, ends[-1] + margin / 2]


def rows_of(slots: list[Slot], columns: int) -> list[list[Slot]]:
    return [slots[index : index + columns] for index in range(0, len(slots), columns)]


def band_of(row: list[Slot]) -> float:
    return HEADING_BAND if any(slot.heading for slot in row) else 0


def row_height(row: list[Slot]) -> float:
    return band_of(row) + max(slot.image.height for slot in row)


def column_width(slots: list[Slot], column: int, columns: int) -> float:
    return max(frame_width(slot) for slot in slots[column::columns])


def placed(slot: Slot, left: float, width: float, top: float, band: float) -> Place:
    outer = frame_width(slot)
    frame_left = left + (width - outer) / 2
    image = Box(frame_left + (outer - slot.image.width) / 2, top + band, slot.image.width, slot.image.height)
    title_room = HEADING_BAND if slot.heading else 0
    frame = Box(frame_left, image.y - title_room, outer, slot.image.height + title_room)
    return Place(image, frame)


def arranged(slots: list[Slot], columns: int, gap: float, margin: float) -> Sheet:
    rows = rows_of(slots, columns)
    widths = [column_width(slots, column, columns) for column in range(columns)]
    heights = [row_height(row) for row in rows]
    lefts, tops = starts(widths, gap, margin), starts(heights, gap, margin)
    places = [
        placed(
            slot,
            lefts[index % columns],
            widths[index % columns],
            tops[index // columns],
            band_of(rows[index // columns]),
        )
        for index, slot in enumerate(slots)
    ]
    size = Size(ceil(lefts[-1] + widths[-1] + margin), ceil(tops[-1] + heights[-1] + margin))
    return Sheet(size, places, channels(lefts, widths, margin), channels(tops, heights, margin))


def refuse_oversize(size: Size, scale: float, where: str) -> None:
    width, height = ceil(size.width * scale), ceil(size.height * scale)
    fits = max(width, height) <= SIDE_LIMIT
    demand(fits, f"{where}: scheme is {width}x{height} px, over the limit of {SIDE_LIMIT} a side")
