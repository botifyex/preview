from typing import Any

from helpers import near
from PIL import Image

DEFAULT_HEX = "#E6004C"
REMOVED_HEX = "#C81E1E"
SPEC_HEX = "#0050C8"
FIGURE_HEX = "#008040"
ANNOTATION_HEX = "#7A00CC"
FRAME_POINT = (296, 224)


def rgb(color: str) -> tuple[int, int, int]:
    return (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16))


def exact(image: Image.Image, point: tuple[int, int], color: tuple[int, int, int]) -> bool:
    return near(image.getpixel(point), color, 0)


def marks_of(manifest: dict[str, Any], index: int = 0) -> list[dict[str, Any]]:
    return manifest["figures"][index]["marks"]


def removed(**extra: Any) -> dict[str, Any]:
    return {"kind": "removed", "anchor": {"selector": "#block"}, "offset": {"y": 100}, **extra}
