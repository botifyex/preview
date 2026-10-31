from typing import Any, cast
from urllib.parse import quote

from helpers import Pixel
from PIL import Image

PAGE = """<!doctype html><style>
html { background: #fff; }
body { margin: 0; height: 1000px; }
div { position: absolute; }
#target { left: 500px; top: 300px; width: 200px; height: 60px; background: #ddeeff; }
#ink { left: 560px; top: 320px; width: 40px; height: 20px; background: #000; }
#first { left: 100px; top: 100px; width: 100px; height: 40px; background: #eee; }
#second { left: 500px; top: 100px; width: 100px; height: 40px; background: #eee; }
#inner { left: 120px; top: 110px; width: 20px; height: 20px; }
</style><div id="target"></div><div id="ink"></div><div id="first"></div><div id="second"></div>
<div id="inner"></div>"""

URL = "data:text/html," + quote(PAGE)
FILLED_URL = "data:text/html," + quote(
    "<!doctype html><style>html, body { margin: 0; height: 100%; } #all { height: 100%; }</style><div id=all></div>"
)
TARGET = {"x": 500, "y": 300, "width": 200, "height": 60}
TARGET_FRAME = {"x": 496, "y": 296, "width": 208, "height": 68}
SENTENCE = "The export now includes credit notes, so its totals match the accounting report."
WHITE = (255, 255, 255)
TARGET_COLOR = (221, 238, 255)


def on(selector: str) -> dict[str, str]:
    return {"selector": selector}


def shape(kind: str, selector: str = "#target", **extra: Any) -> dict[str, Any]:
    return {"kind": kind, "anchor": on(selector), **extra}


def callout(selector: str = "#target", text: str = SENTENCE, **extra: Any) -> dict[str, Any]:
    return shape("callout", selector, text=text, **extra)


def connector(**extra: Any) -> dict[str, Any]:
    return shape("connector", "#second", **{"from": on("#first"), **extra})


def blend(under: tuple[int, int, int], over: tuple[int, int, int], opacity: float) -> tuple[int, int, int]:
    red, green, blue = (round(low * (1 - opacity) + high * opacity) for low, high in zip(under, over, strict=True))
    return (red, green, blue)


def luminance(color: Pixel) -> float:
    channels = [value / 255 for value in cast("tuple[int, int, int]", color)]
    linear = [value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(first: Pixel, second: Pixel) -> float:
    lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def colors_in(image: Image.Image, area: tuple[int, int, int, int]) -> set[tuple[int, ...]]:
    colors = image.crop(area).getcolors(maxcolors=1 << 24) or []
    return {cast("tuple[int, ...]", color) for _, color in colors}
