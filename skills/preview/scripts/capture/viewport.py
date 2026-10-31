from capture.constants import BADGE_RADIUS, FRAMED_KINDS, LINE_PARTS
from capture.model import Box, Spec, demand, describe_locator


def point_box(point: Spec) -> Box:
    return Box(point["x"], point["y"], 0, 0)


def badge_box(center: Spec) -> Box:
    return Box(center["x"] - BADGE_RADIUS, center["y"] - BADGE_RADIUS, 2 * BADGE_RADIUS, 2 * BADGE_RADIUS)


def drawn_parts(mark: Spec, label: Spec | None) -> list[tuple[str, Box]]:
    parts: list[tuple[str, Box]] = []
    if mark["kind"] in FRAMED_KINDS:
        parts.append(("frame", Box(**mark.get("bounds", mark["rectangle"]))))
    if mark["kind"] == "callout":
        parts.append(("callout block", Box(**mark["rectangle"])))
    parts += [(name, point_box(mark[field])) for name, field in LINE_PARTS.get(mark["kind"], ())]
    if mark["badge"] is not None:
        parts.append(("number", badge_box(mark["badge"])))
    if label is not None:
        parts.append(("label", Box(**label)))
    return parts


def demand_visible(box: Box, name: str, page_size: Spec, where: str) -> None:
    left, top = page_size["left"], page_size["top"]
    right, bottom = left + page_size["viewportWidth"], top + page_size["viewportHeight"]
    demand(
        box.inside(left, top, right, bottom),
        f"{where}: {name} is outside the viewport; scroll or resize so it fits, or try full_page from the top",
    )


def check_viewport(
    targets: list[Spec], boxes: list[Box], marks: list[Spec], labels: list[Spec | None], page_size: Spec, where: str
) -> None:
    for target, box in zip(targets, boxes, strict=True):
        demand_visible(box, describe_locator(target), page_size, where)
    for mark, label in zip(marks, labels, strict=True):
        for part, box in drawn_parts(mark, label):
            demand_visible(box, f"{part} of {mark['anchor_description']}", page_size, where)
