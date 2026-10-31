import json
from pathlib import Path
from typing import Any, cast

from capture.colors import validate_color
from capture.constants import DEFAULT_PLACEMENT, FLAG_FIELDS, PRODUCTION_NAMES, SLUG_PATTERN, THEMES
from capture.fields import demand_object, demand_string, demand_url, is_choice, is_integer, is_positive
from capture.items import validate_annotations, validate_locator, validate_placement, validate_steps
from capture.model import CaptureFailure, Spec, demand


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


def validate_figure(figure: Any, index: int) -> None:
    demand_object(figure, f"figure {index}: must be an object")
    slug = figure.get("slug", "")
    where = f"figure {index} ({slug})"
    demand(is_slug(slug), f"{where}: slug must be lowercase words joined by hyphens")
    demand("url" in figure, f"{where}: url is required")
    demand_url(figure, "url", where)
    demand_url(figure, "before_url", where)
    validate_figure_options(figure, where)
    validate_steps(figure, "steps", where, where)
    validate_annotations(figure, "annotations", where, where)
    validate_steps(figure, "before_steps", where, f"{where} before")
    validate_annotations(figure, "before_annotations", where, f"{where} before")


def validate_environment(spec: Spec) -> None:
    environment = spec.get("environment", "")
    demand(isinstance(environment, str), "spec: environment must be a string")
    name = environment.strip().lower()
    demand(name, "spec: environment is required")
    demand(name not in PRODUCTION_NAMES, f"spec: refusing to run against environment '{name}'")
    demand(spec.get("base_url"), "spec: base_url is required")
    demand_url(spec, "base_url", "spec")


def validate_login(login: Any) -> None:
    demand_object(login, "login: must be an object")
    demand(is_slug(login.get("name", "")), "login: name must be lowercase words joined by hyphens")
    demand(login.get("steps"), "login: steps are required")
    validate_steps(login, "steps", "login", "login")
    demand("expect" in login, "login: expect is required, it proves the login worked")
    validate_locator(login["expect"], "login expect")


def validate_hide(hide: Any) -> None:
    valid = isinstance(hide, list) and all(isinstance(selector, str) for selector in cast("list[object]", hide))
    demand(valid, "spec: hide must be a list of selectors")


def validate_figures(figures: Any) -> None:
    demand(figures, "spec: figures are required")
    demand(isinstance(figures, list), "spec: figures must be a list")
    for index, figure in enumerate(figures, 1):
        validate_figure(figure, index)


def validate_spec(spec: Any) -> None:
    demand_object(spec, "spec: must be an object")
    validate_environment(spec)
    demand_string(spec, "locale", "spec")
    validate_hide(spec.get("hide", []))
    validate_placement(spec.get("placement", DEFAULT_PLACEMENT), "spec")
    validate_color(spec, "spec")
    validate_figures(spec.get("figures"))
    if "login" in spec:
        validate_login(spec["login"])


def read_spec(path: Path) -> Spec:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError) as failure:
        raise CaptureFailure(f"cannot read spec {path}: {failure}") from failure
