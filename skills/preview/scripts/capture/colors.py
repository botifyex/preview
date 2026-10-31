from typing import Any

from capture.constants import COLOR_PATTERN, DEFAULT_COLOR, KIND_COLORS
from capture.model import Spec, demand


def is_color(value: Any) -> bool:
    return isinstance(value, str) and COLOR_PATTERN.fullmatch(value) is not None


def validate_color(owner: Spec, where: str) -> None:
    if "color" in owner:
        demand(is_color(owner["color"]), f"{where}: color must be #RRGGBB")


def resolve_color(kind: str, own: Spec, *inherited: Spec) -> str:
    fixed = KIND_COLORS.get(kind)
    levels = [own] if fixed else [own, *inherited]
    fallback = fixed or DEFAULT_COLOR
    return next((level["color"] for level in levels if "color" in level), fallback).upper()
