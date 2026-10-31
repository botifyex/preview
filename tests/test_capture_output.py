import json

import pytest
from capture_support import LOGIN, Capture, account_login, box, figure
from PIL import Image
from support import run_script


def test_miss_in_second_figure_leaves_no_output(capture: Capture) -> None:
    capture.failure(figure(box("#save")), figure(box("#missing"), slug="other"))
    assert not (capture.out / "figures").exists()
    assert [path.name for path in capture.out.iterdir()] == ["failures"]


def test_failed_run_keeps_earlier_output(capture: Capture) -> None:
    capture.figures(figure(slug="kept"))
    process = capture.run({"figures": [figure(box("#missing"), slug="other")]})
    assert process.returncode == 1
    names = sorted(path.name for path in (capture.out / "figures").iterdir())
    assert names == ["01-kept.png", "manifest.json", "spec.json"]
    assert sorted(path.name for path in capture.out.iterdir()) == ["failures", "figures"]


def test_figures_are_numbered_sequentially_with_padding(capture: Capture) -> None:
    manifest = capture.figures(figure(slug="first"), figure(slug="second"), figure(slug="third"))
    assert [entry["file"] for entry in manifest["figures"]] == [
        "figures/01-first.png",
        "figures/02-second.png",
        "figures/03-third.png",
    ]
    assert [entry["number"] for entry in manifest["figures"]] == [1, 2, 3]
    for entry in manifest["figures"]:
        assert (capture.out / entry["file"]).is_file()


def test_second_run_removes_stale_figures(capture: Capture) -> None:
    capture.figures(figure(slug="first"), figure(slug="second"))
    capture.figures(figure(slug="only"))
    names = sorted(path.name for path in (capture.out / "figures").iterdir())
    assert names == ["01-only.png", "manifest.json", "spec.json"]


def test_error_status_is_not_screenshotted(capture: Capture) -> None:
    assert "404" in capture.failure(figure(url="missing.html"))


def test_failure_saves_a_picture_outside_figures_and_names_it(capture: Capture) -> None:
    message = capture.failure(figure(box("#missing"), slug="broken"))
    picture = capture.out / "failures" / "broken.png"
    assert str(picture) in message
    assert Image.open(picture).width == 1280
    assert not (capture.out / "figures").exists()


def test_failed_login_saves_a_picture(capture: Capture) -> None:
    login = {**account_login("a@example.com"), "expect": {"selector": "#absent"}}
    message = capture.failure(figure(url="/account"), login=login)
    assert str(capture.out / "failures" / "login.png") in message
    assert (capture.out / "failures" / "login.png").is_file()


def test_next_run_clears_old_failure_pictures(capture: Capture) -> None:
    capture.failure(figure(box("#missing"), slug="broken"))
    capture.figures(figure(slug="fine"))
    assert not (capture.out / "failures").exists()


def test_spec_is_saved_beside_the_figures_without_secrets(capture: Capture, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXTURE_PASSWORD", "throwaway-secret")
    capture.figures(figure(box("#welcome"), url="panel.html"), login=LOGIN)
    saved = (capture.out / "figures" / "spec.json").read_text()
    assert json.loads(saved)["login"] == LOGIN
    assert "throwaway-secret" not in saved


def test_saved_spec_repeats_the_run(capture: Capture) -> None:
    capture.figures(figure(box("#save")))
    saved = capture.out / "figures" / "spec.json"
    copy = capture.directory / "again.json"
    copy.write_text(saved.read_text())
    process = run_script("capture.py", str(copy), "--out", str(capture.directory / "again"))
    assert process.returncode == 0, process.stderr
