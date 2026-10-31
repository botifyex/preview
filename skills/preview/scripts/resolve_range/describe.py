import re
from pathlib import Path
from typing import Any

from resolve_range.git import commit_of, read_commits, read_files
from resolve_range.model import Span
from resolve_range.spans import automatic_span, explicit_span
from resolve_range.versions import parse_version


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
