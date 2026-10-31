import re
from pathlib import Path

from resolve_range.git import commit_of, git
from resolve_range.model import Stage, Version

STAGE_WORDS: dict[str, Stage] = {
    "alpha": Stage.ALPHA,
    "a": Stage.ALPHA,
    "beta": Stage.BETA,
    "b": Stage.BETA,
    "rc": Stage.CANDIDATE,
    "c": Stage.CANDIDATE,
}
VERSION_PATTERN: re.Pattern[str] = re.compile(
    r"v?(?P<major>\d+)\.(?P<minor>\d+)(?:\.(?P<patch>\d+))?"
    r"(?:[-._]?(?P<stage>alpha|beta|rc|a|b|c)(?:[-._]?(?P<number>\d+))?)?"
    r"(?:\+[0-9A-Za-z.-]+)?",
    re.IGNORECASE | re.ASCII,
)


def parse_version(tag: str, commit: str) -> Version | None:
    match = VERSION_PATTERN.fullmatch(tag)
    if match is None:
        return None
    word = match["stage"]
    return Version(
        tag=tag,
        release=(int(match["major"]), int(match["minor"]), int(match["patch"] or 0)),
        stage=STAGE_WORDS[word.lower()] if word else Stage.STABLE,
        number=int(match["number"] or 0),
        commit=commit,
    )


def reachable_versions(repository: Path, end: str) -> list[Version]:
    names = git(repository, "tag", "--merged", end).split()
    parsed = (parse_version(name, commit_of(repository, name)) for name in names if VERSION_PATTERN.fullmatch(name))
    return sorted((version for version in parsed if version), key=lambda version: version.order)
