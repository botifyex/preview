#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any


class RangeFailure(Exception):
    pass


class Stage(IntEnum):
    ALPHA = 0
    BETA = 1
    CANDIDATE = 2
    STABLE = 3


STAGE_WORDS: dict[str, Stage] = {
    "alpha": Stage.ALPHA,
    "a": Stage.ALPHA,
    "beta": Stage.BETA,
    "b": Stage.BETA,
    "rc": Stage.CANDIDATE,
    "c": Stage.CANDIDATE,
}
BETA_CHANNEL: frozenset[Stage] = frozenset({Stage.BETA, Stage.CANDIDATE})
VERSION_PATTERN: re.Pattern[str] = re.compile(
    r"v?(?P<major>\d+)\.(?P<minor>\d+)(?:\.(?P<patch>\d+))?"
    r"(?:[-._]?(?P<stage>alpha|beta|rc|a|b|c)(?:[-._]?(?P<number>\d+))?)?"
    r"(?:\+[0-9A-Za-z.-]+)?",
    re.IGNORECASE,
)
FIELD_SEPARATOR = "\x00"
COMMIT_FORMAT = "%H%x00%s%x00%b%x00"


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


def git(repository: Path, *arguments: str) -> str:
    process = subprocess.run(
        ["git", "-C", str(repository), *arguments], capture_output=True, text=True
    )
    if process.returncode != 0:
        raise RangeFailure(f"git {arguments[0]} failed: {process.stderr.strip()}")
    return process.stdout


def commit_of(repository: Path, reference: str) -> str:
    process = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "--verify", "--quiet", f"{reference}^{{commit}}"],
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        raise RangeFailure(f"'{reference}' is not a commit in {repository}")
    return process.stdout.strip()


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
    parsed = (parse_version(name, commit_of(repository, name)) for name in names)
    return sorted((version for version in parsed if version), key=lambda version: version.order)


def tag_at(versions: list[Version], commit: str, end: str) -> str:
    matching = [version.tag for version in versions if version.commit == commit]
    return matching[-1] if matching else end


def earlier_than(candidates: list[Version], latest: Version) -> list[Version]:
    return [
        version
        for version in candidates
        if version.order < latest.order and version.commit != latest.commit
    ]


def closing_span(candidates: list[Version], latest: Version, channel: str) -> Span:
    earlier = earlier_than(candidates, latest)
    if not earlier:
        raise RangeFailure(
            f"{latest.tag} is the first {channel} tag and the end of the range: "
            "nothing earlier to compare with, pass --from <ref>"
        )
    return Span(earlier[-1].tag, latest.tag)


def release_span(versions: list[Version], commit: str, end: str) -> Span:
    stable = [version for version in versions if version.stable]
    if not stable:
        raise RangeFailure(f"no stable version tag is reachable from {end}: pass --from <ref>")
    latest = stable[-1]
    if latest.commit == commit:
        return closing_span(stable, latest, "stable")
    return Span(latest.tag, end)


def beta_span(versions: list[Version], commit: str, end: str) -> Span:
    betas = [version for version in versions if version.beta]
    if not betas:
        raise RangeFailure(f"no beta or rc version tag is reachable from {end}: pass --from <ref>")
    latest = betas[-1]
    if latest.commit == commit:
        boundaries = [version for version in versions if version.beta or version.stable]
        return closing_span(boundaries, latest, "beta")
    stable = [version for version in versions if version.stable and version.order > latest.order]
    if not stable:
        return Span(latest.tag, end)
    newest = stable[-1]
    if newest.commit == commit:
        note = f"{newest.tag} is a stable release at the end of the range, showing what changed since the last beta {latest.tag}"
        return Span(latest.tag, newest.tag, (note,))
    note = f"stable {newest.tag} is newer than the last beta {latest.tag}, so the range starts at {newest.tag}: earlier changes are already released"
    return Span(newest.tag, end, (note,))


def automatic_span(repository: Path, mode: str, end: str) -> Span:
    commit = commit_of(repository, end)
    versions = reachable_versions(repository, end)
    if not versions:
        raise RangeFailure(f"no version tags are reachable from {end}: pass --from <ref>")
    if mode == "release":
        return release_span(versions, commit, end)
    return beta_span(versions, commit, end)


def explicit_span(repository: Path, start: str, end: str) -> Span:
    commit = commit_of(repository, end)
    return Span(start, tag_at(reachable_versions(repository, end), commit, end))


def read_commits(repository: Path, start: str, end: str) -> list[dict[str, str]]:
    output = git(repository, "log", f"--format={COMMIT_FORMAT}", f"{start}..{end}")
    fields = output.split(FIELD_SEPARATOR)
    triples = zip(fields[0::3], fields[1::3], fields[2::3], strict=False)
    return [
        {"hash": commit.strip(), "subject": subject, "body": body.strip()}
        for commit, subject, body in triples
    ]


def read_files(repository: Path, start: str, end: str) -> list[dict[str, str]]:
    output = git(repository, "diff", "--name-status", "--no-renames", "-z", start, end)
    fields = output.split(FIELD_SEPARATOR)
    return [
        {"status": status, "path": path} for status, path in zip(fields[0::2], fields[1::2], strict=False)
    ]


def label_of(span: Span, tagged_end: bool) -> str:
    text = span.end if tagged_end else f"{span.start}..{span.end}"
    return re.sub(r"[^0-9A-Za-z._-]+", "-", text.replace("..", "--"))


def describe(repository: Path, mode: str, span: Span) -> dict[str, Any]:
    start_commit = commit_of(repository, span.start)
    end_commit = commit_of(repository, span.end)
    return {
        "mode": mode,
        "from": span.start,
        "to": span.end,
        "from_commit": start_commit,
        "to_commit": end_commit,
        "label": label_of(span, parse_version(span.end, end_commit) is not None),
        "notes": list(span.notes),
        "commits": read_commits(repository, span.start, span.end),
        "files": read_files(repository, span.start, span.end),
    }


def resolve(repository: Path, mode: str, start: str | None, end: str) -> dict[str, Any]:
    span = explicit_span(repository, start, end) if start else automatic_span(repository, mode, end)
    return describe(repository, mode, span)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Resolve the git range of a preview")
    result.add_argument("mode", choices=["release", "beta"])
    result.add_argument("--repo", type=Path, default=Path.cwd())
    result.add_argument("--from", dest="start")
    result.add_argument("--to", dest="end", default="HEAD")
    return result


def main() -> int:
    arguments = parser().parse_args()
    try:
        report = resolve(arguments.repo, arguments.mode, arguments.start, arguments.end)
    except RangeFailure as failure:
        print(f"error: {failure}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
