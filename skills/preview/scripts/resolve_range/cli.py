import argparse
import json
import sys
from pathlib import Path
from typing import Any

from resolve_range.describe import resolve
from resolve_range.model import RangeFailure


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Resolve the git range of a preview")
    result.add_argument("mode", choices=["release", "beta"])
    result.add_argument("--repo", type=Path, default=Path.cwd())
    result.add_argument("--from", dest="start")
    result.add_argument("--to", dest="end", default="HEAD")
    return result


def emit(report: dict[str, Any]) -> None:
    text = json.dumps(report, indent=2, ensure_ascii=False)
    sys.stdout.buffer.write(f"{text}\n".encode(errors="replace"))


def main() -> int:
    arguments = parser().parse_args()
    try:
        report = resolve(arguments.repo, arguments.mode, arguments.start, arguments.end)
    except RangeFailure as failure:
        print(f"error: {failure}", file=sys.stderr)
        return 1
    emit(report)
    return 0
