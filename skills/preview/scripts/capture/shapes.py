import math
from dataclasses import asdict, dataclass

from capture.constants import (
    BOX_PADDING,
    CONNECTOR_MINIMUM,
    EDGE_MARGIN,
    ELLIPSE_REACH,
    HIGHLIGHT_OPACITY,
    SPOTLIGHT_OPACITY,
)
from capture.model import Box, CaptureFailure, Spec, demand, describe_locator


def clamp_frame(box: Box, area: Box) -> Box:
    left = max(area.x + EDGE_MARGIN, box.x - BOX_PADDING)
    top = max(area.y + EDGE_MARGIN, box.y - BOX_PADDING)
    right = min(area.right - EDGE_MARGIN, box.right + BOX_PADDING)
    bottom = min(area.bottom - EDGE_MARGIN, box.bottom + BOX_PADDING)
    return Box(left, top, right - left, bottom - top)


def edge_scale(half_width: float, half_height: float, delta_x: float, delta_y: float) -> float:
    return min(
        half_width / abs(delta_x) if delta_x else math.inf,
        half_height / abs(delta_y) if delta_y else math.inf,
    )


@dataclass(frozen=True)
class Placed:
    box: Box
    source: Box | None
    annotation: Spec
    page_size: Spec
    area: Box
    where: str

    @property
    def frame(self) -> Box:
        return clamp_frame(self.box, self.area)


def ellipse_bounds(frame: Box, area: Box) -> Box:
    center_x, center_y = frame.center
    reach_x, reach_y = frame.width / 2 * ELLIPSE_REACH, frame.height / 2 * ELLIPSE_REACH
    left = max(area.x + EDGE_MARGIN, center_x - reach_x)
    top = max(area.y + EDGE_MARGIN, center_y - reach_y)
    right = min(area.right - EDGE_MARGIN, center_x + reach_x)
    bottom = min(area.bottom - EDGE_MARGIN, center_y + reach_y)
    return Box(left, top, right - left, bottom - top)


def ellipse_fields(placed: Placed) -> Spec:
    bounds = ellipse_bounds(placed.frame, placed.area)
    return {"bounds": asdict(bounds), "top": bounds.y, "bottom": bounds.bottom}


def underline_fields(placed: Placed) -> Spec:
    frame = placed.frame
    return {
        "start": {"x": max(placed.box.x, frame.x), "y": frame.bottom},
        "end": {"x": min(placed.box.right, frame.right), "y": frame.bottom},
    }


def highlight_fields(_placed: Placed) -> Spec:
    return {"opacity": HIGHLIGHT_OPACITY}


def spotlight_fields(placed: Placed) -> Spec:
    size = placed.page_size
    return {
        "opacity": SPOTLIGHT_OPACITY,
        "veil": {
            "width": max(size["width"], size["left"] + size["viewportWidth"]),
            "height": max(size["height"], size["top"] + size["viewportHeight"]),
        },
    }


def connector_fields(placed: Placed) -> Spec:
    anchor = describe_locator(placed.annotation["anchor"])
    if placed.source is None:
        raise CaptureFailure(f"{placed.where}: connector to {anchor} has no from")
    frame, other = placed.frame, clamp_frame(placed.source, placed.area)
    anchor_x, anchor_y = frame.center
    source_x, source_y = other.center
    delta_x, delta_y = source_x - anchor_x, source_y - anchor_y
    near = edge_scale(frame.width / 2, frame.height / 2, delta_x, delta_y)
    far = edge_scale(other.width / 2, other.height / 2, delta_x, delta_y)
    room = math.hypot(delta_x, delta_y) * (1 - near - far)
    demand(
        room >= CONNECTOR_MINIMUM, f"{placed.where}: connector to {anchor} has no room, the elements touch or overlap"
    )
    middle_x, middle_y = (anchor_x + source_x) / 2, (anchor_y + source_y) / 2
    return {
        "source": asdict(placed.source),
        "heads": placed.annotation.get("heads", "none"),
        "start": {"x": source_x - delta_x * far, "y": source_y - delta_y * far},
        "end": {"x": anchor_x + delta_x * near, "y": anchor_y + delta_y * near},
        "corner": {"x": middle_x, "y": middle_y},
        "bottom": middle_y,
    }
