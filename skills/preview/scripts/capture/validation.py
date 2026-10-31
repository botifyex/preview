import json
import re
from pathlib import Path
from typing import Any, cast

from capture.constants import (
    ANNOTATION_FIELDS,
    ARROW_PLACEMENTS,
    DEFAULT_PLACEMENT,
    FLAG_FIELDS,
    LOCATOR_KEYS,
    MATCH_KINDS,
    PLACEMENTS,
    PRODUCTION_NAMES,
    SLUG_PATTERN,
    STEP_FIELDS,
    THEMES,
)
from capture.model import CaptureFailure, Spec, demand


def validate_match(target: Spec, where: str) -> None:
    kind = target.get("match", "exact")
    demand(kind in MATCH_KINDS, f"{where}: match must be exact, substring or regex")
    if "match" not in target:
        return
    pattern: Any = target.get("text", target.get("name"))
    demand(pattern is not None, f"{where}: match applies to text or a role name")
    if kind == "regex":
        try:
            re.compile(pattern)
        except re.error as failure:
            raise CaptureFailure(f"{where}: match regex is invalid: {failure}") from failure


def validate_locator(target: Any, where: str) -> None:
    demand(isinstance(target, dict), f"{where}: target must be an object")
    keys = LOCATOR_KEYS & set(target)
    demand(len(keys) == 1, f"{where}: exactly one of selector, role, text is required")
    validate_match(target, where)


def validate_step(step: Spec, where: str) -> None:
    kind: Any = step.get("action")
    demand(kind in STEP_FIELDS, f"{where}: unknown action {kind!r}")
    missing = STEP_FIELDS[kind] - set(step)
    demand(not missing, f"{where}: {kind} requires {sorted(missing)}")
    if "target" in step:
        validate_locator(step["target"], where)
    if kind == "fill":
        demand(("value" in step) != ("value_env" in step), f"{where}: fill requires value or value_env")
    if kind == "wait":
        demand(("target" in step) != ("milliseconds" in step), f"{where}: wait requires target or milliseconds")


def validate_steps(steps: list[Spec], where: str) -> None:
    for index, step in enumerate(steps, 1):
        validate_step(step, f"{where} step {index}")


def validate_placement(placement: Any, where: str) -> None:
    demand(placement in PLACEMENTS, f"{where}: placement must be one of {sorted(PLACEMENTS)}")


def validate_annotation(annotation: Spec, where: str) -> None:
    kind: Any = annotation.get("kind")
    demand(kind in ANNOTATION_FIELDS, f"{where}: unknown annotation kind {kind!r}")
    missing = ANNOTATION_FIELDS[kind] - set(annotation)
    demand(not missing, f"{where}: {kind} requires {sorted(missing)}")
    validate_locator(annotation["anchor"], where)
    validate_placement(annotation.get("placement", DEFAULT_PLACEMENT), where)
    if kind == "arrow":
        placement = annotation.get("placement", DEFAULT_PLACEMENT)
        demand(placement in ARROW_PLACEMENTS, f"{where}: placement {placement} does not apply to an arrow")
    if "from" in annotation:
        validate_locator(annotation["from"], where)


def validate_annotations(annotations: list[Spec], where: str) -> None:
    for index, annotation in enumerate(annotations, 1):
        validate_annotation(annotation, f"{where} annotation {index}")


def validate_figure(figure: Spec, index: int) -> None:
    slug = figure.get("slug", "")
    where = f"figure {index} ({slug})"
    demand(SLUG_PATTERN.fullmatch(slug), f"{where}: slug must be lowercase words joined by hyphens")
    demand("url" in figure, f"{where}: url is required")
    demand(figure.get("theme", "light") in THEMES, f"{where}: theme must be light or dark")
    validate_placement(figure.get("placement", DEFAULT_PLACEMENT), where)
    for name in FLAG_FIELDS:
        demand(isinstance(figure.get(name, False), bool), f"{where}: {name} must be true or false")
    demand(figure.get("login", True) in (True, False), f"{where}: login may only be false")
    validate_steps(figure.get("steps", []), where)
    validate_annotations(figure.get("annotations", []), where)
    validate_steps(figure.get("before_steps", []), f"{where} before")
    validate_annotations(figure.get("before_annotations", []), f"{where} before")


def validate_environment(spec: Spec) -> None:
    environment = str(spec.get("environment", "")).strip().lower()
    demand(environment, "spec: environment is required")
    demand(environment not in PRODUCTION_NAMES, f"spec: refusing to run against environment '{environment}'")
    demand(spec.get("base_url"), "spec: base_url is required")


def validate_login(login: Spec) -> None:
    demand(SLUG_PATTERN.fullmatch(login.get("name", "")), "login: name must be lowercase words joined by hyphens")
    demand(login.get("steps"), "login: steps are required")
    validate_steps(login["steps"], "login")
    demand("expect" in login, "login: expect is required, it proves the login worked")
    validate_locator(login["expect"], "login expect")


def validate_hide(hide: Any) -> None:
    valid = isinstance(hide, list) and all(isinstance(selector, str) for selector in cast("list[object]", hide))
    demand(valid, "spec: hide must be a list of selectors")


def validate_spec(spec: Spec) -> None:
    validate_environment(spec)
    validate_hide(spec.get("hide", []))
    validate_placement(spec.get("placement", DEFAULT_PLACEMENT), "spec")
    demand(spec.get("figures"), "spec: figures are required")
    for index, figure in enumerate(spec["figures"], 1):
        validate_figure(figure, index)
    if "login" in spec:
        validate_login(spec["login"])


def read_spec(path: Path) -> Spec:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as failure:
        raise CaptureFailure(f"cannot read spec {path}: {failure}") from failure
