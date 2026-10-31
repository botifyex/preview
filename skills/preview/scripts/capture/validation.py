import json
from pathlib import Path
from typing import Any, cast

from capture.colors import validate_color
from capture.constants import DEFAULT_PLACEMENT, PRODUCTION_NAMES
from capture.fields import demand_object, demand_string, demand_url
from capture.figure_fields import is_slug, validate_figure_options
from capture.items import validate_annotations, validate_locator, validate_placement, validate_steps
from capture.model import CaptureFailure, Spec, demand
from capture.scheme.validation import validate_scheme


def validate_figure(figure: Any, index: int) -> None:
    demand_object(figure, f"figure {index}: must be an object")
    slug = figure.get("slug", "")
    where = f"figure {index} ({slug})"
    demand(is_slug(slug), f"{where}: slug must be lowercase words joined by hyphens")
    if "panels" in figure:
        validate_scheme(figure, where)
        return
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
