from collections.abc import Callable
from dataclasses import asdict

from capture.callout import callout_fields, demand_number_clear
from capture.constants import (
    ARROW_REACH,
    BADGE_INSET,
    BADGE_MARGIN,
    BADGE_REACH,
    BOX_PADDING,
    DEFAULT_PLACEMENT,
    KIND_PLACEMENTS,
    OUTSIDE_PLACEMENTS,
    PLACEMENTS,
    TAIL_PLACEMENTS,
)
from capture.model import Box, Spec, demand, describe_locator
from capture.shapes import (
    Placed,
    clamp_frame,
    connector_fields,
    edge_scale,
    ellipse_fields,
    highlight_fields,
    spotlight_fields,
    underline_fields,
)

SHAPE_FIELDS: dict[str, Callable[[Placed], Spec]] = {
    "callout": callout_fields,
    "connector": connector_fields,
    "ellipse": ellipse_fields,
    "highlight": highlight_fields,
    "spotlight": spotlight_fields,
    "underline": underline_fields,
}


def page_area(page_size: Spec) -> Box:
    return Box(0, 0, page_size["width"], page_size["height"])


def visible_area(page_size: Spec) -> Box:
    return Box(page_size["left"], page_size["top"], page_size["viewportWidth"], page_size["viewportHeight"])


def removed_place(box: Box, annotation: Spec) -> Box:
    offset = annotation["offset"]
    return Box(
        box.x + offset.get("x", 0),
        box.y + offset.get("y", 0),
        offset.get("width", box.width),
        offset.get("height", box.height),
    )


def default_tail(box: Box, area: Box) -> tuple[float, float]:
    center_x, center_y = box.center
    reach_x = box.width / 2 + ARROW_REACH[0]
    reach_y = box.height / 2 + ARROW_REACH[1]
    x = center_x - reach_x if center_x - reach_x >= area.x else center_x + reach_x
    y = center_y - reach_y if center_y - reach_y >= area.y else center_y + reach_y
    return (min(x, area.right), min(y, area.bottom))


def arrow_tail(box: Box, source: Box | None, annotation: Spec, area: Box) -> tuple[float, float]:
    if source is not None:
        return source.center
    if "offset" in annotation:
        offset = annotation["offset"]
        center_x, center_y = box.center
        return (center_x + offset.get("x", 0), center_y + offset.get("y", 0))
    return default_tail(box, area)


def arrow_tip(box: Box, tail: tuple[float, float], where: str) -> tuple[float, float]:
    center_x, center_y = box.center
    delta_x, delta_y = tail[0] - center_x, tail[1] - center_y
    half_width, half_height = box.width / 2 + BOX_PADDING, box.height / 2 + BOX_PADDING
    scale = edge_scale(half_width, half_height, delta_x, delta_y)
    demand(scale < 1, f"{where}: arrow starts inside its target")
    return (center_x + delta_x * scale, center_y + delta_y * scale)


def inside_page(box: Box, page_size: Spec) -> bool:
    return box.inside(0, 0, page_size["width"], page_size["height"])


def geometry(kind: str, box: Box, source: Box | None, annotation: Spec, page_size: Spec, area: Box, where: str) -> Spec:
    if kind == "removed":
        place = removed_place(box, annotation)
        demand(inside_page(place, page_size), f"{where}: removed marker falls outside the page")
        frame = clamp_frame(place, page_area(page_size))
        return {"rectangle": asdict(frame), "corner": {"x": frame.x, "y": frame.y}, "bottom": frame.bottom}
    frame = clamp_frame(box, area)
    corner = {"x": frame.x, "y": frame.y}
    result: Spec = {"rectangle": asdict(frame), "corner": corner, "bottom": frame.bottom}
    if kind == "arrow":
        tail = arrow_tail(box, source, annotation, area)
        demand(
            0 <= tail[0] <= page_size["width"] and 0 <= tail[1] <= page_size["height"],
            f"{where}: arrow starts outside the page",
        )
        tip = arrow_tip(box, tail, where)
        result |= {"tail": {"x": tail[0], "y": tail[1]}, "tip": {"x": tip[0], "y": tip[1]}}
        result["corner"] = {"x": tail[0], "y": tail[1]}
        result["bottom"] = tail[1]
    if kind in SHAPE_FIELDS:
        result |= SHAPE_FIELDS[kind](Placed(box, source, annotation, page_size, area, where))
    return result


def clamped_badge(corner: Spec, area: Box) -> Spec:
    return {
        "x": max(area.x + BADGE_MARGIN, min(area.right - BADGE_MARGIN, corner["x"])),
        "y": max(area.y + BADGE_MARGIN, min(area.bottom - BADGE_MARGIN, corner["y"])),
    }


def outside_badge(placement: str, frame: Box, page_size: Spec, where: str) -> Spec:
    middle_x, middle_y = frame.center
    x, y = {
        "left": (frame.x - BADGE_REACH, middle_y),
        "right": (frame.right + BADGE_REACH, middle_y),
        "above": (middle_x, frame.y - BADGE_REACH),
        "below": (middle_x, frame.bottom + BADGE_REACH),
    }[placement]
    fits = (
        BADGE_MARGIN <= x <= page_size["width"] - BADGE_MARGIN
        and BADGE_MARGIN <= y <= page_size["height"] - BADGE_MARGIN
    )
    demand(fits, f"{where}: badge placed {placement} falls outside the page")
    return {"x": x, "y": y}


def inside_badge(frame: Box, where: str) -> Spec:
    fits = frame.width >= 2 * BADGE_INSET and frame.height >= 2 * BADGE_INSET
    demand(fits, f"{where}: shape is too small for a number placed inside")
    return {"x": frame.x + BADGE_INSET, "y": frame.y + BADGE_INSET}


def corner_point(placement: str, frame: Box) -> Spec:
    return {
        "top-right": {"x": frame.right, "y": frame.y},
        "bottom-left": {"x": frame.x, "y": frame.bottom},
        "bottom-right": {"x": frame.right, "y": frame.bottom},
    }[placement]


def badge_center(placement: str, shape: Spec, page_size: Spec, area: Box, where: str) -> Spec:
    frame = Box(**shape["rectangle"])
    outer = Box(**shape.get("bounds", shape["rectangle"]))
    if placement in TAIL_PLACEMENTS:
        return clamped_badge(shape["corner"], area)
    if placement in OUTSIDE_PLACEMENTS:
        return outside_badge(placement, outer, page_size, where)
    if placement == "inside":
        return inside_badge(frame, where)
    return clamped_badge(corner_point(placement, frame), page_area(page_size))


def applicable_placement(annotation: Spec) -> str:
    placement = annotation.get("placement", DEFAULT_PLACEMENT)
    return placement if placement in KIND_PLACEMENTS.get(annotation["kind"], PLACEMENTS) else DEFAULT_PLACEMENT


def build_mark(annotation: Spec, box: Box, source: Box | None, page_size: Spec, area: Box, where: str) -> Spec:
    kind = annotation["kind"]
    shape = geometry(kind, box, source, annotation, page_size, area, where)
    placement = applicable_placement(annotation)
    numbered = annotation.get("number") is not None
    badge = badge_center(placement, shape, page_size, area, where) if numbered else None
    if badge is not None and kind == "callout":
        demand_number_clear(badge, box, annotation["anchor"], where)
    return {
        "kind": kind,
        "color": annotation["color"],
        "number": annotation.get("number"),
        "text": annotation.get("text"),
        "anchor_description": describe_locator(annotation["anchor"]),
        "element": asdict(box),
        "badge": badge,
        **shape,
    }


def build_marks(annotations: list[Spec], boxes: list[Box], page_size: Spec, area: Box, where: str) -> list[Spec]:
    remaining = iter(boxes)
    marks: list[Spec] = []
    for annotation in annotations:
        box = next(remaining)
        source = next(remaining) if "from" in annotation else None
        marks.append(build_mark(annotation, box, source, page_size, area, where))
    return marks
