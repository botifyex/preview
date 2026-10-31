import math
from dataclasses import asdict

from capture.constants import (
    BADGE_RADIUS,
    CALLOUT_GAP,
    CALLOUT_LINE,
    CALLOUT_PADDING,
    CALLOUT_SIDES,
    CALLOUT_WIDTH,
    EDGE_MARGIN,
)
from capture.model import Box, CaptureFailure, Spec, demand, describe_locator
from capture.shapes import Placed


def wrap_limit(annotation: Spec, area: Box) -> float:
    default = min(CALLOUT_WIDTH, area.width - 2 * EDGE_MARGIN)
    return annotation.get("width", default) - 2 * CALLOUT_PADDING[0]


def bounded(value: float, lowest: float, highest: float) -> float:
    return max(lowest, min(highest, value))


def side_block(side: str, frame: Box, width: float, height: float, area: Box) -> Box:
    center_x, center_y = frame.center
    across = bounded(center_y - height / 2, area.y + EDGE_MARGIN, area.bottom - EDGE_MARGIN - height)
    along = bounded(center_x - width / 2, area.x + EDGE_MARGIN, area.right - EDGE_MARGIN - width)
    x, y = {
        "left": (frame.x - CALLOUT_GAP - width, across),
        "right": (frame.right + CALLOUT_GAP, across),
        "above": (along, frame.y - CALLOUT_GAP - height),
        "below": (along, frame.bottom + CALLOUT_GAP),
    }[side]
    return Box(x, y, width, height)


def fits(block: Box, area: Box) -> bool:
    return block.inside(area.x + EDGE_MARGIN, area.y + EDGE_MARGIN, area.right - EDGE_MARGIN, area.bottom - EDGE_MARGIN)


def choose_side(placed: Placed, width: float, height: float) -> tuple[str, Box]:
    annotation = placed.annotation
    sides = (annotation["side"],) if "side" in annotation else CALLOUT_SIDES
    for side in sides:
        block = side_block(side, placed.frame, width, height, placed.area)
        if fits(block, placed.area):
            return side, block
    named = annotation.get("side", "any side")
    anchor = describe_locator(annotation["anchor"])
    raise CaptureFailure(f"{placed.where}: callout does not fit {named} of {anchor}")


def leader_points(side: str, frame: Box, block: Box) -> tuple[Spec, Spec]:
    center_x, center_y = frame.center
    level = bounded(center_y, block.y, block.bottom)
    column = bounded(center_x, block.x, block.right)
    return {
        "left": ({"x": block.right, "y": level}, {"x": frame.x, "y": center_y}),
        "right": ({"x": block.x, "y": level}, {"x": frame.right, "y": center_y}),
        "above": ({"x": column, "y": block.bottom}, {"x": center_x, "y": frame.y}),
        "below": ({"x": column, "y": block.y}, {"x": center_x, "y": frame.bottom}),
    }[side]


def placed_lines(lines: list[str], block: Box) -> list[Spec]:
    return [
        {
            "text": line,
            "x": block.x + CALLOUT_PADDING[0],
            "y": block.y + CALLOUT_PADDING[1] + CALLOUT_LINE * (index + 0.5),
        }
        for index, line in enumerate(lines)
    ]


def callout_fields(placed: Placed) -> Spec:
    measured = placed.annotation["measured"]
    anchor = describe_locator(placed.annotation["anchor"])
    demand(measured["lines"] and measured["width"] > 0, f"{placed.where}: callout text draws nothing on {anchor}")
    width = math.ceil(measured["width"]) + 2 * CALLOUT_PADDING[0]
    height = len(measured["lines"]) * CALLOUT_LINE + 2 * CALLOUT_PADDING[1]
    side, block = choose_side(placed, width, height)
    start, end = leader_points(side, placed.frame, block)
    return {
        "rectangle": asdict(block),
        "corner": {"x": block.x, "y": block.y},
        "bottom": block.bottom,
        "side": side,
        "start": start,
        "end": end,
        "lines": placed_lines(measured["lines"], block),
    }


def demand_number_clear(badge: Spec, box: Box, anchor: Spec, where: str) -> None:
    apart = (
        badge["x"] + BADGE_RADIUS <= box.x
        or badge["x"] - BADGE_RADIUS >= box.right
        or badge["y"] + BADGE_RADIUS <= box.y
        or badge["y"] - BADGE_RADIUS >= box.bottom
    )
    demand(apart, f"{where}: number of the callout covers {describe_locator(anchor)}")
