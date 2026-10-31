import re
from typing import Any

from capture.colors import validate_color
from capture.constants import (
    ANNOTATION_FIELDS,
    ARROW_PLACEMENTS,
    DEFAULT_PLACEMENT,
    LOCATOR_KEYS,
    MATCH_KINDS,
    PLACEMENTS,
    STEP_FIELDS,
)
from capture.fields import (
    demand_list,
    demand_object,
    demand_string,
    demand_url,
    is_choice,
    is_integer,
    is_number,
    is_positive,
)
from capture.model import CaptureFailure, Spec, demand


def validate_pattern(pattern: str, where: str) -> None:
    try:
        re.compile(pattern)
    except (re.error, OverflowError, RecursionError) as failure:
        raise CaptureFailure(f"{where}: match regex is invalid: {failure}") from failure


def validate_match(target: Spec, where: str) -> None:
    kind = target.get("match", "exact")
    demand(is_choice(kind, MATCH_KINDS), f"{where}: match must be exact, substring or regex")
    if "match" not in target:
        return
    pattern: Any = target.get("text", target.get("name"))
    demand(pattern is not None, f"{where}: match applies to text or a role name")
    if kind == "regex":
        validate_pattern(pattern, where)


def validate_locator(target: Any, where: str) -> None:
    demand_object(target, f"{where}: target must be an object")
    keys = LOCATOR_KEYS & set(target)
    demand(len(keys) == 1, f"{where}: exactly one of selector, role, text is required")
    for field in (*sorted(LOCATOR_KEYS), "name"):
        demand_string(target, field, where)
    validate_match(target, where)


def validate_wait(step: Spec, where: str) -> None:
    demand(("target" in step) != ("milliseconds" in step), f"{where}: wait requires target or milliseconds")
    if "milliseconds" in step:
        duration = step["milliseconds"]
        demand(is_number(duration) and duration >= 0, f"{where}: milliseconds must be a number from 0")


def validate_step(step: Any, where: str) -> None:
    demand_object(step, f"{where}: must be an object")
    kind: Any = step.get("action")
    demand(is_choice(kind, STEP_FIELDS), f"{where}: unknown action {kind!r}")
    missing = STEP_FIELDS[kind] - set(step)
    demand(not missing, f"{where}: {kind} requires {sorted(missing)}")
    demand_url(step, "url", where)
    for field in ("value", "value_env", "key"):
        demand_string(step, field, where)
    if "target" in step:
        validate_locator(step["target"], where)
    if kind == "fill":
        demand(("value" in step) != ("value_env" in step), f"{where}: fill requires value or value_env")
    if kind == "wait":
        validate_wait(step, where)


def validate_steps(owner: Spec, field: str, where: str, label: str) -> None:
    for index, step in enumerate(demand_list(owner, field, where), 1):
        validate_step(step, f"{label} step {index}")


def validate_placement(placement: Any, where: str) -> None:
    demand(is_choice(placement, PLACEMENTS), f"{where}: placement must be one of {sorted(PLACEMENTS)}")


def validate_offset(offset: Any, where: str) -> None:
    demand_object(offset, f"{where}: offset must be an object")
    for field in ("x", "y"):
        demand(is_number(offset.get(field, 0)), f"{where}: offset {field} must be a number")
    for field in ("width", "height"):
        demand(is_positive(offset.get(field, 1)), f"{where}: offset {field} must be a positive number")


def validate_marking(annotation: Spec, where: str) -> None:
    if "number" in annotation:
        demand(is_integer(annotation["number"]), f"{where}: number must be an integer")
    demand_string(annotation, "text", where)
    if "offset" in annotation:
        validate_offset(annotation["offset"], where)


def validate_annotation(annotation: Any, where: str) -> None:
    demand_object(annotation, f"{where}: must be an object")
    kind: Any = annotation.get("kind")
    demand(is_choice(kind, ANNOTATION_FIELDS), f"{where}: unknown annotation kind {kind!r}")
    missing = ANNOTATION_FIELDS[kind] - set(annotation)
    demand(not missing, f"{where}: {kind} requires {sorted(missing)}")
    validate_locator(annotation["anchor"], where)
    validate_placement(annotation.get("placement", DEFAULT_PLACEMENT), where)
    validate_color(annotation, where)
    if kind == "arrow":
        placement = annotation.get("placement", DEFAULT_PLACEMENT)
        demand(placement in ARROW_PLACEMENTS, f"{where}: placement {placement} does not apply to an arrow")
    if "from" in annotation:
        validate_locator(annotation["from"], where)
    validate_marking(annotation, where)


def validate_annotations(owner: Spec, field: str, where: str, label: str) -> None:
    for index, annotation in enumerate(demand_list(owner, field, where), 1):
        validate_annotation(annotation, f"{label} annotation {index}")
