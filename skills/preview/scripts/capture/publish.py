import json
import shutil
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from capture.constants import BACKUP_PREFIX, FIGURE_PATTERN, INCOMING_NAME, MANIFEST_NAME, SPEC_NAME
from capture.model import CaptureFailure, Spec, demand


@dataclass(frozen=True)
class Move:
    source: Path
    target: Path


def field_of(value: Any, name: str) -> Any:
    return cast("Spec", value).get(name) if isinstance(value, dict) else None


def manifest_files(figures: Path) -> list[Any]:
    try:
        manifest = json.loads((figures / MANIFEST_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError):
        return []
    entries = field_of(manifest, "figures")
    if not isinstance(entries, list):
        return []
    return [field_of(item, "file") for item in cast("list[Any]", entries)]


def base_names(files: list[Any]) -> set[str]:
    if not all(isinstance(file, str) for file in files):
        return set()
    return {Path(file).name for file in files}


def regular(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def owned_names(figures: Path) -> set[str]:
    listed = {name for name in base_names(manifest_files(figures)) if FIGURE_PATTERN.fullmatch(name)}
    return {name for name in listed | {MANIFEST_NAME, SPEC_NAME} if regular(figures / name)}


def refuse_foreign(names: list[str], figures: Path, owned: set[str]) -> None:
    for name in sorted(names):
        foreign = name not in owned and (figures / name).exists(follow_symlinks=False)
        demand(not foreign, f"{figures / name} already exists and was not created by this tool")


def refuse_conflicts(names: list[str], figures: Path) -> None:
    usable = figures.is_dir() or not figures.exists(follow_symlinks=False)
    demand(usable, f"{figures} already exists and is not a directory")
    refuse_foreign([*names, MANIFEST_NAME, SPEC_NAME], figures, owned_names(figures))


def write_records(staging: Path, entries: list[Spec], spec: Spec) -> None:
    manifest = {"environment": spec["environment"], "base_url": spec["base_url"], "figures": entries}
    for name, content in ((MANIFEST_NAME, manifest), (SPEC_NAME, spec)):
        text = json.dumps(content, indent=2, ensure_ascii=False) + "\n"
        (staging / name).write_text(text, encoding="utf-8")


def received(staging: Path, backup: Path) -> Path:
    incoming = backup / INCOMING_NAME
    incoming.mkdir()
    for new in sorted(staging.iterdir()):
        shutil.move(new, incoming / new.name)
    return incoming


def planned_moves(incoming: Path, figures: Path, backup: Path, owned: set[str]) -> list[Move]:
    retiring = [Move(figures / name, backup / name) for name in sorted(owned)]
    arriving = [Move(new, figures / new.name) for new in sorted(incoming.iterdir())]
    return retiring + arriving


def perform(moves: list[Move], done: list[Move]) -> None:
    for move in moves:
        done.append(move)
        move.source.replace(move.target)


def performed(move: Move) -> bool:
    return move.target.exists(follow_symlinks=False) and not move.source.exists(follow_symlinks=False)


def undo(done: list[Move], backup: Path) -> None:
    try:
        for move in reversed(done):
            if performed(move):
                move.target.replace(move.source)
    except OSError as failure:
        raise CaptureFailure(f"cannot restore earlier figures, they remain in {backup}: {failure}") from failure


def discard_incoming(backup: Path) -> None:
    shutil.rmtree(backup / INCOMING_NAME, ignore_errors=True)
    try:
        backup.rmdir()
    except OSError as failure:
        raise CaptureFailure(f"cannot restore earlier figures, they remain in {backup}: {failure}") from failure


def swap(staging: Path, figures: Path, owned: set[str]) -> None:
    backup = Path(tempfile.mkdtemp(dir=figures, prefix=BACKUP_PREFIX))
    done: list[Move] = []
    try:
        perform(planned_moves(received(staging, backup), figures, backup, owned), done)
    except BaseException:
        undo(done, backup)
        discard_incoming(backup)
        raise
    shutil.rmtree(backup, ignore_errors=True)


def publish_into(staging: Path, figures: Path, entries: list[Spec], spec: Spec) -> None:
    owned = owned_names(figures)
    write_records(staging, entries, spec)
    refuse_foreign([new.name for new in staging.iterdir()], figures, owned)
    swap(staging, figures, owned)


def discard_new(figures: Path, existed: bool) -> None:
    if not existed:
        with suppress(OSError):
            figures.rmdir()


def publish(staging: Path, figures: Path, entries: list[Spec], spec: Spec) -> None:
    existed = figures.exists(follow_symlinks=False)
    try:
        figures.mkdir(parents=True, exist_ok=True)
        publish_into(staging, figures, entries, spec)
    except CaptureFailure:
        discard_new(figures, existed)
        raise
    except (OSError, ValueError) as failure:
        discard_new(figures, existed)
        raise CaptureFailure(f"cannot publish figures: {failure}") from failure
