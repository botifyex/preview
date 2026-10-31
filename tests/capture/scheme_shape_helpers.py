from collections.abc import Iterator
from typing import Any, NamedTuple
from urllib.parse import quote

from helpers import ACCENT, REMOVED
from scheme_helpers import BLUE_PIXEL, GREEN_PIXEL, panel, scheme
from shape_helpers import SENTENCE, WHITE, blend

PAGE = quote(
    """<!doctype html><style>
html { background: #ccccff; }
body { margin: 0; height: 600px; }
div { position: absolute; }
#area { left: 60px; top: 40px; width: 520px; height: 360px; }
#target { left: 340px; top: 180px; width: 120px; height: 60px; background: #00aa00; }
#source { left: 120px; top: 180px; width: 80px; height: 60px; background: #0000aa; }
#beyond { left: 640px; top: 460px; width: 60px; height: 40px; background: #aa00aa; }
#beside { left: 20px; top: 180px; width: 18px; height: 60px; background: #aa00aa; }
</style><div id="area"></div><div id="target"></div><div id="source"></div><div id="beyond"></div>
<div id="beside"></div>"""
)
URL = "data:text/html," + PAGE
VIEWPORT = {"width": 800, "height": 600, "scale": 1}
AREA = {"selector": "#area"}
PADDING = 20
SHOWN_LEFT, SHOWN_TOP = 40, 20
PANEL_WIDTH = 420
SCALE = 0.75
FIGURE = "02-composite.png"
SINGLE_FIGURE = "01-composite.png"
SOURCE_PIXEL = (0, 0, 170)
BLACK = (0, 0, 0)
DIMMED_BLUE = blend(BLUE_PIXEL, BLACK, 0.6)
TINTED_GREEN = blend(GREEN_PIXEL, ACCENT, 0.25)

SOURCE = {"selector": "#source"}
EXTRAS: dict[str, dict[str, Any]] = {
    "arrow": {"from": SOURCE},
    "callout": {"text": SENTENCE, "side": "above"},
    "connector": {"from": SOURCE},
    "label": {"text": "Totals"},
    "removed": {"offset": {"y": -100}},
}
KINDS = (
    "box",
    "arrow",
    "badge",
    "label",
    "removed",
    "callout",
    "ellipse",
    "underline",
    "highlight",
    "spotlight",
    "connector",
)
NEW_KINDS = ("callout", "ellipse", "underline", "highlight", "spotlight", "connector")


class Probe(NamedTuple):
    name: str
    x: float
    y: float
    color: tuple[int, int, int]
    reach: int = 1


def annotation(kind: str) -> dict[str, Any]:
    return {"kind": kind, "anchor": {"selector": "#target"}, "number": 1, **EXTRAS.get(kind, {})}


def cropped(*annotations: dict[str, Any], **extra: Any) -> dict[str, Any]:
    settings: dict[str, Any] = {"url": URL, "crop": AREA, "crop_padding": PADDING, **extra}
    return panel(annotations=list(annotations), **settings)


def composite(*panels: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return scheme(*panels, slug="composite", viewport=VIEWPORT, panel_width=PANEL_WIDTH, **extra)


def middle(first: dict[str, float], second: dict[str, float]) -> tuple[float, float]:
    return ((first["x"] + second["x"]) / 2, (first["y"] + second["y"]) / 2)


def center_of(box: dict[str, float]) -> tuple[float, float]:
    return (box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)


def frame_probes(mark: dict[str, Any], color: tuple[int, int, int]) -> list[Probe]:
    rectangle = mark["rectangle"]
    return [Probe("rectangle top", center_of(rectangle)[0], rectangle["y"], color)]


def label_probes(mark: dict[str, Any]) -> list[Probe]:
    corner = mark["corner"]
    return [Probe("corner", corner["x"] + 24 * SCALE, corner["y"] - 20 * SCALE, ACCENT)]


def callout_probes(mark: dict[str, Any]) -> list[Probe]:
    block, line = mark["rectangle"], mark["lines"][0]
    return [
        Probe("block", block["x"] + block["width"] - 4, block["y"] + block["height"] - 4, ACCENT),
        Probe("leader", *middle(mark["start"], mark["end"]), ACCENT),
        Probe("line", line["x"] + 20, line["y"], WHITE, 6),
    ]


def ellipse_probes(mark: dict[str, Any]) -> list[Probe]:
    bounds = mark["bounds"]
    across, down = center_of(bounds)
    return [
        Probe("top", across, mark["top"], ACCENT),
        Probe("bottom", across, mark["bottom"], ACCENT),
        Probe("bounds", bounds["x"], down, ACCENT),
    ]


def spotlight_probes(mark: dict[str, Any]) -> list[Probe]:
    rectangle = mark["rectangle"]
    across, down = center_of(rectangle)
    return [
        Probe("hole", across, down, GREEN_PIXEL),
        Probe("veil", rectangle["x"] - 8, down, DIMMED_BLUE),
    ]


def connector_probes(mark: dict[str, Any]) -> list[Probe]:
    return [
        Probe("line", *middle(mark["start"], mark["corner"]), ACCENT),
        Probe("source", *center_of(mark["source"]), SOURCE_PIXEL),
    ]


def box_probes(mark: dict[str, Any]) -> list[Probe]:
    return frame_probes(mark, ACCENT)


def removed_probes(mark: dict[str, Any]) -> list[Probe]:
    return frame_probes(mark, REMOVED)


def arrow_probes(mark: dict[str, Any]) -> list[Probe]:
    return [Probe("shaft", *middle(mark["tail"], mark["tip"]), ACCENT)]


def badge_probes(mark: dict[str, Any]) -> list[Probe]:
    return [Probe("number", mark["badge"]["x"] - 7, mark["badge"]["y"], ACCENT)]


def underline_probes(mark: dict[str, Any]) -> list[Probe]:
    return [Probe("line", *middle(mark["start"], mark["end"]), ACCENT)]


def highlight_probes(mark: dict[str, Any]) -> list[Probe]:
    return [Probe("fill", *center_of(mark["rectangle"]), TINTED_GREEN)]


PROBES = {
    "box": box_probes,
    "arrow": arrow_probes,
    "badge": badge_probes,
    "label": label_probes,
    "removed": removed_probes,
    "callout": callout_probes,
    "ellipse": ellipse_probes,
    "underline": underline_probes,
    "highlight": highlight_probes,
    "spotlight": spotlight_probes,
    "connector": connector_probes,
}


def probes_of(mark: dict[str, Any]) -> list[Probe]:
    return PROBES[mark["kind"]](mark)


def leaves(value: Any, path: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], Any]]:
    if isinstance(value, dict):
        for key, item in value.items():  # pyright: ignore[reportUnknownVariableType]
            yield from leaves(item, (*path, str(key)))  # pyright: ignore[reportUnknownArgumentType]
    elif isinstance(value, list):
        for index, item in enumerate(value):  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
            yield from leaves(item, (*path, str(index)))
    else:
        yield path, value
