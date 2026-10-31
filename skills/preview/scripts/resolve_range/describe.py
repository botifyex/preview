import re
from pathlib import Path
from typing import Any

from resolve_range.git import commit_of, is_tag, read_commits, read_files
from resolve_range.model import RangeFailure, Span
from resolve_range.spans import automatic_span, explicit_span
from resolve_range.versions import parse_version


def label_of(span: Span, tagged_end: bool) -> str:
    text = span.end if tagged_end else f"{span.start}..{span.end}"
    return re.sub(r"[^0-9A-Za-z._-]+", "-", text.replace("..", "--"))


def ends_at_version(repository: Path, span: Span, commit: str) -> bool:
    return parse_version(span.end, commit) is not None and is_tag(repository, span.end)


def describe(repository: Path, mode: str, span: Span) -> dict[str, Any]:
    start_commit = commit_of(repository, span.start)
    end_commit = commit_of(repository, span.end)
    return {
        "mode": mode,
        "from": span.start,
        "to": span.end,
        "from_commit": start_commit,
        "to_commit": end_commit,
        "label": label_of(span, ends_at_version(repository, span, end_commit)),
        "notes": list(span.notes),
        "commits": read_commits(repository, span.start, span.end),
        "files": read_files(repository, span.start, span.end),
    }


def require_reference(flag: str, reference: str | None) -> None:
    if reference == "":
        raise RangeFailure(f"{flag} must not be empty")


def resolve(repository: Path, mode: str, start: str | None, end: str) -> dict[str, Any]:
    require_reference("--from", start)
    require_reference("--to", end)
    span = automatic_span(repository, mode, end) if start is None else explicit_span(repository, start, end)
    return describe(repository, mode, span)
