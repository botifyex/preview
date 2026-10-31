import errno
import json
import os
import shutil
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from helpers import Capture, box, figure
from internals import internal


def contents(directory: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in directory.iterdir() if path.is_file()}


def staged(directory: Path, *names: str) -> Path:
    directory.mkdir()
    for name in names:
        (directory / name).write_bytes(b"new " + name.encode())
    return directory


REPOSITORY = Path(__file__).resolve().parent.parent.parent
SPEC = {"environment": "test", "base_url": "http://example.test/"}


def entries_for(*names: str) -> list[dict[str, Any]]:
    return [{"file": f"figures/{name}"} for name in names]


def earlier_output(root: Path) -> Path:
    figures = root / "figures"
    names = ("01-old.png", "02-old.png")
    internal("publish").publish(staged(root / "first", *names), figures, entries_for(*names), SPEC)
    return figures


class FailingMoves:
    def __init__(self, original: Callable[..., None], *positions: int) -> None:
        self.positions: tuple[int, ...] = positions
        self.original: Callable[..., None] = original
        self.calls: int = 0
        self.fired: bool = False

    def __call__(self, source: Any, target: Any) -> None:
        self.calls += 1
        if self.calls - 1 in self.positions:
            self.fired = True
            raise OSError("injected")
        self.original(source, target)


@pytest.mark.parametrize("position", range(8))
def test_failure_at_any_move_restores_the_earlier_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, position: int
) -> None:
    module = internal("publish")
    failure_type = internal("model").CaptureFailure
    figures = earlier_output(tmp_path)
    before = contents(figures)
    names = ("01-new.png", "02-old.png")
    staging = staged(tmp_path / "second", *names)
    moves = FailingMoves(os.replace, position)
    monkeypatch.setattr(os, "replace", moves)
    with pytest.raises(failure_type, match="injected"):
        module.publish(staging, figures, entries_for(*names), SPEC)
    monkeypatch.undo()
    assert moves.fired
    assert contents(figures) == before
    assert sorted(path.name for path in figures.iterdir()) == sorted(before)


@pytest.mark.parametrize("position", [1, 3, 4, 6])
def test_failed_restore_keeps_the_backup_and_names_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, position: int
) -> None:
    figures = earlier_output(tmp_path)
    before = contents(figures)
    names = ("01-new.png", "02-old.png")
    staging = staged(tmp_path / "second", *names)
    monkeypatch.setattr(os, "replace", FailingMoves(os.replace, position, position + 1))
    with pytest.raises(internal("model").CaptureFailure, match=r"\.capture-backup-") as caught:
        internal("publish").publish(staging, figures, entries_for(*names), SPEC)
    monkeypatch.undo()
    backup = next(path for path in figures.iterdir() if path.name.startswith(".capture-backup-"))
    assert str(backup) in str(caught.value)
    kept = contents(backup)
    for name, content in before.items():
        assert content in (kept.get(name), contents(figures).get(name)), name


class InterruptedMoves:
    def __init__(self, original: Callable[..., None], position: int, performed: bool) -> None:
        self.original: Callable[..., None] = original
        self.position: int = position
        self.performed: bool = performed
        self.calls: int = 0

    def __call__(self, source: Any, target: Any) -> None:
        self.calls += 1
        if self.calls - 1 != self.position:
            self.original(source, target)
            return
        if self.performed:
            self.original(source, target)
        raise KeyboardInterrupt


@pytest.mark.parametrize("performed", [True, False], ids=["after-move", "before-move"])
@pytest.mark.parametrize("position", range(8))
def test_interrupt_at_any_move_restores_the_earlier_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, position: int, performed: bool
) -> None:
    figures = earlier_output(tmp_path)
    before = contents(figures)
    names = ("01-new.png", "02-old.png")
    staging = staged(tmp_path / "second", *names)
    monkeypatch.setattr(os, "replace", InterruptedMoves(os.replace, position, performed))
    with pytest.raises(KeyboardInterrupt):
        internal("publish").publish(staging, figures, entries_for(*names), SPEC)
    monkeypatch.undo()
    assert contents(figures) == before
    assert sorted(path.name for path in figures.iterdir()) == sorted(before)


def test_retired_file_that_cannot_return_stays_in_the_named_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    figures = earlier_output(tmp_path)
    old = (figures / "01-old.png").read_bytes()
    names = ("01-new.png",)
    staging = staged(tmp_path / "second", *names)
    original = os.replace

    def occupied(source: Any, target: Any) -> None:
        original(source, target)
        if Path(source).name == "01-old.png" and not (figures / "01-old.png").exists():
            (figures / "01-old.png").write_bytes(b"mine")
            raise OSError("injected")

    monkeypatch.setattr(os, "replace", occupied)
    with pytest.raises(internal("model").CaptureFailure, match=r"\.capture-backup-") as caught:
        internal("publish").publish(staging, figures, entries_for(*names), SPEC)
    monkeypatch.undo()
    backup = next(path for path in figures.iterdir() if path.name.startswith(".capture-backup-"))
    assert str(backup) in str(caught.value)
    assert (backup / "01-old.png").read_bytes() == old
    assert (figures / "01-old.png").read_bytes() == b"mine"
    assert not (backup / "incoming").exists()


def test_failure_while_receiving_changes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    figures = earlier_output(tmp_path)
    before = contents(figures)
    names = ("01-new.png",)
    staging = staged(tmp_path / "second", *names)

    def refuse(_source: Any, _target: Any) -> None:
        raise OSError("injected")

    monkeypatch.setattr(shutil, "move", refuse)
    with pytest.raises(internal("model").CaptureFailure, match="injected"):
        internal("publish").publish(staging, figures, entries_for(*names), SPEC)
    monkeypatch.undo()
    assert sorted(path.name for path in figures.iterdir()) == sorted(before)
    assert contents(figures) == before


@pytest.fixture
def other_device() -> Iterator[Path]:
    directory = Path(tempfile.mkdtemp(dir=REPOSITORY, prefix=".capture-test-"))
    yield directory
    shutil.rmtree(directory)


@pytest.fixture
def linked_figures(capture: Capture, other_device: Path) -> Path:
    if capture.directory.stat().st_dev == other_device.stat().st_dev:
        pytest.skip("no second filesystem between the temporary directory and the repository")
    capture.out.mkdir()
    (capture.out / "figures").symlink_to(other_device, target_is_directory=True)
    return other_device


def test_figures_on_another_filesystem_are_published(capture: Capture, linked_figures: Path) -> None:
    capture.figures(figure(slug="first"), figure(slug="second"))
    capture.figures(figure(slug="only"))
    assert sorted(path.name for path in linked_figures.iterdir()) == ["01-only.png", "manifest.json", "spec.json"]


@pytest.mark.parametrize("position", range(8))
def test_failure_on_another_filesystem_restores(
    tmp_path: Path, other_device: Path, monkeypatch: pytest.MonkeyPatch, position: int
) -> None:
    if tmp_path.stat().st_dev == other_device.stat().st_dev:
        pytest.skip("no second filesystem between the temporary directory and the repository")
    module = internal("publish")
    names = ("01-old.png", "02-old.png")
    module.publish(staged(tmp_path / "first", *names), other_device, entries_for(*names), SPEC)
    before = contents(other_device)
    fresh = ("01-new.png", "02-old.png")
    staging = staged(tmp_path / "second", *fresh)
    moves = FailingMoves(os.replace, position)
    monkeypatch.setattr(os, "replace", moves)
    with pytest.raises(internal("model").CaptureFailure, match="injected"):
        module.publish(staging, other_device, entries_for(*fresh), SPEC)
    monkeypatch.undo()
    assert moves.fired
    assert contents(other_device) == before
    assert sorted(path.name for path in other_device.iterdir()) == sorted(before)


def test_cross_device_error_is_handled_without_a_second_filesystem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    figures = earlier_output(tmp_path)
    original = os.rename

    def crossing(source: Any, target: Any) -> None:
        if Path(source).parent.name == "second":
            raise OSError(errno.EXDEV, "cross-device")
        original(source, target)

    monkeypatch.setattr(os, "rename", crossing)
    names = ("01-new.png",)
    internal("publish").publish(staged(tmp_path / "second", *names), figures, entries_for(*names), SPEC)
    monkeypatch.undo()
    assert sorted(path.name for path in figures.iterdir()) == ["01-new.png", "manifest.json", "spec.json"]


def test_conflict_is_refused_before_the_browser_starts(capture: Capture, monkeypatch: pytest.MonkeyPatch) -> None:
    capture.figures(figure(slug="kept"))
    figures = capture.out / "figures"
    (figures / "01-fresh.png").write_bytes(b"mine")
    before = contents(figures)
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(capture.directory / "no-browsers"))
    process = capture.run({"figures": [figure(slug="fresh")]})
    assert process.returncode == 1
    assert "01-fresh.png" in process.stderr
    assert "cannot start Chromium" not in process.stderr
    assert contents(figures) == before


def test_figures_path_taken_by_a_file_is_refused_before_the_browser_starts(
    capture: Capture, monkeypatch: pytest.MonkeyPatch
) -> None:
    capture.out.mkdir()
    (capture.out / "figures").write_text("mine")
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(capture.directory / "no-browsers"))
    process = capture.run({"figures": [figure()]})
    assert process.returncode == 1
    assert "figures" in process.stderr
    assert "cannot start Chromium" not in process.stderr


def test_conflict_appearing_during_the_run_is_refused_at_publish(tmp_path: Path) -> None:
    figures = earlier_output(tmp_path)
    (figures / "03-fresh.png").write_bytes(b"mine")
    before = contents(figures)
    names = ("03-fresh.png",)
    staging = staged(tmp_path / "second", *names)
    with pytest.raises(internal("model").CaptureFailure, match=r"03-fresh\.png"):
        internal("publish").publish(staging, figures, entries_for(*names), SPEC)
    assert contents(figures) == before


def test_nothing_is_left_behind_after_success(tmp_path: Path) -> None:
    figures = earlier_output(tmp_path)
    names = ("01-new.png",)
    internal("publish").publish(staged(tmp_path / "second", *names), figures, entries_for(*names), SPEC)
    assert sorted(contents(figures)) == ["01-new.png", "manifest.json", "spec.json"]
    assert sorted(path.name for path in tmp_path.iterdir()) == ["figures", "first", "second"]


def test_read_only_figures_keep_the_earlier_output(capture: Capture) -> None:
    capture.figures(figure(slug="kept"))
    figures = capture.out / "figures"
    before = contents(figures)
    figures.chmod(0o500)
    try:
        process = capture.run({"figures": [figure(slug="other")]})
    finally:
        figures.chmod(0o700)
    assert process.returncode == 1
    assert process.stderr.startswith("error: ")
    assert "Traceback" not in process.stderr
    assert contents(figures) == before
    assert sorted(path.name for path in capture.out.iterdir()) == ["figures"]


def test_text_that_cannot_be_saved_keeps_the_earlier_output(capture: Capture) -> None:
    capture.figures(figure(slug="kept"))
    figures = capture.out / "figures"
    before = contents(figures)
    process = capture.run({"figures": [figure(box("#save", text="\ud800"), slug="other")]})
    assert process.returncode == 1
    assert process.stderr.startswith("error: ")
    assert "Traceback" not in process.stderr
    assert contents(figures) == before


def test_figures_path_taken_by_a_file_is_refused(capture: Capture) -> None:
    capture.out.mkdir()
    (capture.out / "figures").write_text("mine")
    process = capture.run({"figures": [figure()]})
    assert process.returncode == 1
    assert process.stderr.startswith("error: ")
    assert "Traceback" not in process.stderr
    assert (capture.out / "figures").read_text() == "mine"


def test_failure_on_a_new_output_leaves_no_figures_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = internal("publish")
    names = ("01-new.png",)
    staging = staged(tmp_path / "first", *names)
    moves = FailingMoves(os.replace, 1)
    monkeypatch.setattr(os, "replace", moves)
    with pytest.raises(internal("model").CaptureFailure):
        module.publish(staging, tmp_path / "figures", entries_for(*names), SPEC)
    monkeypatch.undo()
    assert not (tmp_path / "figures").exists()


def test_directory_on_a_new_figure_name_is_refused_before_anything_changes(capture: Capture) -> None:
    capture.figures(figure(slug="kept"))
    figures = capture.out / "figures"
    before = contents(figures)
    (figures / "02-fresh.png").mkdir()
    process = capture.run({"figures": [figure(slug="other"), figure(slug="fresh")]})
    assert process.returncode == 1
    assert "Traceback" not in process.stderr
    assert "02-fresh.png" in process.stderr
    assert contents(figures) == before
    assert (figures / "02-fresh.png").is_dir()


def test_foreign_file_on_a_new_figure_name_is_refused(capture: Capture) -> None:
    capture.figures(figure(slug="kept"))
    figures = capture.out / "figures"
    (figures / "01-fresh.png").write_bytes(b"mine")
    before = contents(figures)
    process = capture.run({"figures": [figure(slug="fresh")]})
    assert process.returncode == 1
    assert "01-fresh.png" in process.stderr
    assert contents(figures) == before


def test_rerun_replaces_a_figure_it_created(capture: Capture) -> None:
    capture.figures(figure(slug="same"))
    capture.figures(figure(box("#save"), slug="same"))
    assert sorted(contents(capture.out / "figures")) == ["01-same.png", "manifest.json", "spec.json"]


def test_figure_of_someone_else_survives_a_run(capture: Capture) -> None:
    capture.figures(figure(slug="first"))
    figures = capture.out / "figures"
    (figures / "07-mine.png").write_bytes(b"mine")
    capture.figures(figure(slug="second"))
    assert sorted(contents(figures)) == ["01-second.png", "07-mine.png", "manifest.json", "spec.json"]
    assert (figures / "07-mine.png").read_bytes() == b"mine"


@pytest.mark.parametrize(
    "manifest",
    [
        None,
        "{",
        "[]",
        "5",
        '{"figures": 5}',
        '{"figures": [5]}',
        '{"figures": [{"file": 5}]}',
        '{"figures": [{"file": "figures/01-first.png"}, {"file": 5}]}',
        '{"figures": [{"number": 1}]}',
        b"\xff\xfe",
    ],
    ids=["absent", "broken", "list", "number", "figures-number", "entry", "file", "partly", "no-file", "binary"],
)
def test_bad_manifest_makes_no_figure_ours(capture: Capture, manifest: str | bytes | None) -> None:
    capture.figures(figure(slug="first"))
    figures = capture.out / "figures"
    path = figures / "manifest.json"
    path.unlink()
    if manifest is not None:
        path.write_bytes(manifest.encode() if isinstance(manifest, str) else manifest)
    capture.figures(figure(slug="second"), figure(slug="third"))
    assert (figures / "01-first.png").is_file()
    assert (figures / "01-second.png").is_file()
    assert json.loads(path.read_text())["figures"][0]["file"] == "figures/01-second.png"


def rewrite_manifest(figures: Path, *files: str) -> None:
    manifest = {"figures": [{"file": file} for file in files]}
    (figures / "manifest.json").write_text(json.dumps(manifest))


def test_traversal_in_a_manifest_is_not_followed(capture: Capture) -> None:
    capture.figures(figure(slug="first"))
    figures = capture.out / "figures"
    victim = capture.directory / "01-victim.png"
    victim.write_bytes(b"mine")
    rewrite_manifest(figures, "figures/../../01-victim.png", "figures/01-first.png")
    capture.figures(figure(slug="second"))
    assert victim.read_bytes() == b"mine"
    assert not (figures / "01-first.png").exists()


@pytest.mark.parametrize("name", ["notes.txt", "photo.png"])
def test_manifest_cannot_claim_a_name_that_is_not_a_figure(capture: Capture, name: str) -> None:
    capture.figures(figure(slug="first"))
    figures = capture.out / "figures"
    (figures / name).write_bytes(b"mine")
    rewrite_manifest(figures, f"figures/{name}")
    capture.figures(figure(slug="second"))
    assert (figures / name).read_bytes() == b"mine"


def test_listed_directory_is_kept(capture: Capture) -> None:
    capture.figures(figure(slug="first"))
    figures = capture.out / "figures"
    (figures / "05-folder.png").mkdir()
    rewrite_manifest(figures, "figures/05-folder.png", "figures/01-first.png")
    capture.figures(figure(slug="second"))
    assert (figures / "05-folder.png").is_dir()


@pytest.mark.parametrize("name", ["manifest.json", "spec.json"])
def test_directory_named_like_our_file_is_refused(capture: Capture, name: str) -> None:
    capture.figures(figure(slug="first"))
    figures = capture.out / "figures"
    (figures / name).unlink()
    (figures / name).mkdir()
    (figures / name / "inner.txt").write_text("mine")
    process = capture.run({"figures": [figure(slug="second")]})
    assert process.returncode == 1
    assert "Traceback" not in process.stderr
    assert name in process.stderr
    assert (figures / name / "inner.txt").read_text() == "mine"
    assert (figures / "01-first.png").is_file()
