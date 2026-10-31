import math
from dataclasses import asdict

from capture.constants import (
    ARROW_REACH,
    BADGE_INSET,
    BADGE_MARGIN,
    BADGE_REACH,
    BOX_PADDING,
    DEFAULT_PLACEMENT,
    EDGE_MARGIN,
    OUTSIDE_PLACEMENTS,
    TAIL_PLACEMENTS,
)
from capture.model import Box, Spec, demand, describe_locator


def clamp_frame(box: Box, page_size: Spec) -> Box:
    left = max(EDGE_MARGIN, box.x - BOX_PADDING)
    top = max(EDGE_MARGIN, box.y - BOX_PADDING)
    right = min(page_size["width"] - EDGE_MARGIN, box.right + BOX_PADDING)
    bottom = min(page_size["height"] - EDGE_MARGIN, box.bottom + BOX_PADDING)
    return Box(left, top, right - left, bottom - top)


def removed_place(box: Box, annotation: Spec) -> Box:
    offset = annotation["offset"]
    return Box(
        box.x + offset.get("x", 0),
        box.y + offset.get("y", 0),
        offset.get("width", box.width),
        offset.get("height", box.height),
    )


def default_tail(box: Box, page_size: Spec) -> tuple[float, float]:
    center_x, center_y = box.center
    reach_x = box.width / 2 + ARROW_REACH[0]
    reach_y = box.height / 2 + ARROW_REACH[1]
    x = center_x - reach_x if center_x - reach_x >= 0 else center_x + reach_x
    y = center_y - reach_y if center_y - reach_y >= 0 else center_y + reach_y
    return (min(x, page_size["width"]), min(y, page_size["height"]))


def arrow_tail(box: Box, source: Box | None, annotation: Spec, page_size: Spec) -> tuple[float, float]:
    if source is not None:
        return source.center
    if "offset" in annotation:
        offset = annotation["offset"]
        center_x, center_y = box.center
        return (center_x + offset.get("x", 0), center_y + offset.get("y", 0))
    return default_tail(box, page_size)


def arrow_tip(box: Box, tail: tuple[float, float], where: str) -> tuple[float, float]:
    center_x, center_y = box.center
    delta_x, delta_y = tail[0] - center_x, tail[1] - center_y
    half_width, half_height = box.width / 2 + BOX_PADDING, box.height / 2 + BOX_PADDING
    scale = min(
        half_width / abs(delta_x) if delta_x else math.inf,
        half_height / abs(delta_y) if delta_y else math.inf,
    )
    demand(scale < 1, f"{where}: arrow starts inside its target")
    return (center_x + delta_x * scale, center_y + delta_y * scale)


def inside_page(box: Box, page_size: Spec) -> bool:
    return box.inside(0, 0, page_size["width"], page_size["height"])


def geometry(kind: str, box: Box, source: Box | None, annotation: Spec, page_size: Spec, where: str) -> Spec:
    if kind == "removed":
        place = removed_place(box, annotation)
        demand(inside_page(place, page_size), f"{where}: removed marker falls outside the page")
        frame = clamp_frame(place, page_size)
        return {"rectangle": asdict(frame), "corner": {"x": frame.x, "y": frame.y}, "bottom": frame.bottom}
    frame = clamp_frame(box, page_size)
    corner = {"x": frame.x, "y": frame.y}
    result: Spec = {"rectangle": asdict(frame), "corner": corner, "bottom": frame.bottom}
    if kind == "arrow":
        tail = arrow_tail(box, source, annotation, page_size)
        demand(
            0 <= tail[0] <= page_size["width"] and 0 <= tail[1] <= page_size["height"],
            f"{where}: arrow starts outside the page",
        )
        tip = arrow_tip(box, tail, where)
        result |= {"tail": {"x": tail[0], "y": tail[1]}, "tip": {"x": tip[0], "y": tip[1]}}
        result["corner"] = {"x": tail[0], "y": tail[1]}
        result["bottom"] = tail[1]
    return result


def clamped_badge(corner: Spec, page_size: Spec) -> Spec:
    return {
        "x": max(BADGE_MARGIN, min(page_size["width"] - BADGE_MARGIN, corner["x"])),
        "y": max(BADGE_MARGIN, min(page_size["height"] - BADGE_MARGIN, corner["y"])),
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


def badge_center(placement: str, shape: Spec, page_size: Spec, where: str) -> Spec:
    frame = Box(**shape["rectangle"])
    if placement in TAIL_PLACEMENTS:
        return clamped_badge(shape["corner"], page_size)
    if placement in OUTSIDE_PLACEMENTS:
        return outside_badge(placement, frame, page_size, where)
    if placement == "inside":
        return inside_badge(frame, where)
    return clamped_badge(corner_point(placement, frame), page_size)


def build_mark(annotation: Spec, box: Box, source: Box | None, page_size: Spec, where: str) -> Spec:
    kind = annotation["kind"]
    shape = geometry(kind, box, source, annotation, page_size, where)
    placement = annotation.get("placement", DEFAULT_PLACEMENT)
    badge = badge_center(placement, shape, page_size, where) if annotation.get("number") is not None else None
    return {
        "kind": kind,
        "number": annotation.get("number"),
        "text": annotation.get("text"),
        "anchor_description": describe_locator(annotation["anchor"]),
        "element": asdict(box),
        "badge": badge,
        **shape,
    }


def build_marks(annotations: list[Spec], boxes: list[Box], page_size: Spec, where: str) -> list[Spec]:
    remaining = iter(boxes)
    marks: list[Spec] = []
    for annotation in annotations:
        box = next(remaining)
        source = next(remaining) if "from" in annotation else None
        marks.append(build_mark(annotation, box, source, page_size, where))
    return marks


def check_viewport(marks: list[Spec], page_size: Spec, where: str) -> None:
    left, top = page_size["left"], page_size["top"]
    right, bottom = left + page_size["viewportWidth"], top + page_size["viewportHeight"]
    for mark in marks:
        element = Box(**mark["element"])
        demand(
            element.inside(left, top, right, bottom),
            f"{where}: {mark['anchor_description']} is outside the viewport, use full_page",
        )
