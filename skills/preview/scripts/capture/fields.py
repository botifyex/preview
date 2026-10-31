from collections.abc import Collection
from typing import Any
from urllib.parse import urlsplit

from capture.constants import NUMBER_LIMIT
from capture.model import Spec, demand


def is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and -NUMBER_LIMIT <= value <= NUMBER_LIMIT


def is_integer(value: Any) -> bool:
    return is_number(value) and isinstance(value, int)


def is_positive(value: Any) -> bool:
    return is_number(value) and value > 0


def is_choice(value: Any, choices: Collection[str]) -> bool:
    return isinstance(value, str) and value in choices


def is_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        urlsplit(value)
    except ValueError:
        return False
    return True


def demand_object(value: Any, message: str) -> None:
    demand(isinstance(value, dict), message)


def demand_list(owner: Spec, field: str, where: str) -> list[Any]:
    items = owner.get(field, [])
    demand(isinstance(items, list), f"{where}: {field} must be a list")
    return items


def demand_string(owner: Spec, field: str, where: str) -> None:
    if field in owner:
        demand(isinstance(owner[field], str), f"{where}: {field} must be a string")


def demand_url(owner: Spec, field: str, where: str) -> None:
    if field in owner:
        demand(is_url(owner[field]), f"{where}: {field} must be a valid address")
