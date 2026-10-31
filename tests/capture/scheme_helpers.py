from typing import Any

from helpers import Capture, near

VIEWPORT = {"width": 400, "height": 300, "scale": 1}
BLUE, YELLOW, CYAN = "ccccff", "ffffcc", "ccffff"
BLUE_PIXEL, YELLOW_PIXEL = (204, 204, 255), (255, 255, 204)
GREEN_PIXEL = (0, 170, 0)
BACKGROUND_PIXEL = (242, 244, 247)


def panel(shade: str = BLUE, **extra: Any) -> dict[str, Any]:
    return {"url": f"scheme.html#{shade}", **extra}


def scheme(*panels: dict[str, Any], slug: str = "scheme", **extra: Any) -> dict[str, Any]:
    return {"slug": slug, "viewport": VIEWPORT, "panels": list(panels), **extra}


def three(**extra: Any) -> dict[str, Any]:
    return scheme(panel(BLUE), panel(YELLOW), panel(CYAN), **extra)


def center(box: dict[str, Any]) -> tuple[int, int]:
    return (int(box["x"] + box["width"] / 2), int(box["y"] + box["height"] / 2))


def inner_pixel(capture: Capture, name: str, box: dict[str, Any]) -> tuple[int, ...]:
    return capture.image(name).getpixel((int(box["x"]) + 10, int(box["y"]) + 10))  # pyright: ignore[reportReturnType]


def run_scheme(capture: Capture, *figures: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return capture.figures(*figures, **extra)["figures"][0]


def has_color(capture: Capture, name: str, area: tuple[int, int, int, int], color: tuple[int, int, int]) -> bool:
    cropped = capture.image(name).crop(area)
    return any(near(pixel, color) for pixel in cropped.get_flattened_data())
