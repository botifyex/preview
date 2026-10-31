from typing import Any

from capture.colors import validate_color
from capture.constants import DEFAULT_PLACEMENT, FLAG_FIELDS, SLUG_PATTERN, THEMES
from capture.fields import demand_object, is_choice, is_integer, is_positive
from capture.items import validate_placement
from capture.model import Spec, demand


def is_slug(value: Any) -> bool:
    return isinstance(value, str) and SLUG_PATTERN.fullmatch(value) is not None


def validate_viewport(viewport: Any, where: str) -> None:
    demand_object(viewport, f"{where}: viewport must be an object")
    for field in ("width", "height"):
        value = viewport.get(field, 1)
        demand(is_integer(value) and is_positive(value), f"{where}: viewport {field} must be a positive integer")
    demand(is_positive(viewport.get("scale", 1)), f"{where}: viewport scale must be a positive number")


def validate_figure_options(figure: Spec, where: str) -> None:
    demand(is_choice(figure.get("theme", "light"), THEMES), f"{where}: theme must be light or dark")
    validate_placement(figure.get("placement", DEFAULT_PLACEMENT), where)
    validate_color(figure, where)
    for name in (*FLAG_FIELDS, "full_page"):
        demand(isinstance(figure.get(name, False), bool), f"{where}: {name} must be true or false")
    demand(figure.get("login", False) is False, f"{where}: login may only be false")
    validate_viewport(figure.get("viewport", {}), where)
