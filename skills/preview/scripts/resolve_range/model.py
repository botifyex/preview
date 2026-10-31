from dataclasses import dataclass
from enum import IntEnum


class RangeFailure(Exception):
    pass


class Stage(IntEnum):
    ALPHA = 0
    BETA = 1
    CANDIDATE = 2
    STABLE = 3


BETA_CHANNEL: frozenset[Stage] = frozenset({Stage.BETA, Stage.CANDIDATE})


@dataclass(frozen=True)
class Version:
    tag: str
    release: tuple[int, int, int]
    stage: Stage
    number: int
    commit: str

    @property
    def order(self) -> tuple[tuple[int, int, int], Stage, int, str]:
        return (self.release, self.stage, self.number, self.tag)

    @property
    def stable(self) -> bool:
        return self.stage is Stage.STABLE

    @property
    def beta(self) -> bool:
        return self.stage in BETA_CHANNEL


@dataclass(frozen=True)
class Span:
    start: str
    end: str
    notes: tuple[str, ...] = ()
