import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from capture.constants import LOCATOR_KEYS


class CaptureFailure(Exception):
    pass


type Spec = dict[str, Any]


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    width: float
    height: float

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    def inside(self, left: float, top: float, right: float, bottom: float) -> bool:
        return self.x >= left and self.y >= top and self.right <= right and self.bottom <= bottom


@dataclass(frozen=True)
class Options:
    output: Path
    state_directory: Path
    ignore_https: bool
    fresh_login: bool
    timeout: int


@dataclass(frozen=True)
class Shot:
    slug: str
    url: str
    steps: list[Spec]
    annotations: list[Spec]
    figure: Spec
    role: str


def demand(condition: Any, message: str) -> None:
    if not condition:
        raise CaptureFailure(message)


def describe_locator(target: Spec) -> str:
    return json.dumps(
        {key: target[key] for key in sorted(target) if key in LOCATOR_KEYS | {"name", "match"}}, ensure_ascii=False
    )
