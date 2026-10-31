import json
import uuid
from pathlib import Path
from typing import Any

import pytest
from capture_support import LOGIN, Capture, SessionHandler, account_login, box, figure
from support import run_script


def test_login_state_reaches_figures_and_is_gitignored(capture: Capture, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXTURE_PASSWORD", "throwaway-secret")
    manifest = capture.figures(figure(box("#welcome"), url="panel.html"), login=LOGIN)
    assert manifest["figures"][0]["marks"][0]["element"]
    state = next(capture.state.glob("tester-*.json"))
    assert state.stat().st_mode & 0o777 == 0o600
    assert (capture.state / ".gitignore").read_text() == "*\n"
    assert "throwaway-secret" not in (capture.out / "figures" / "manifest.json").read_text()


def test_state_is_reused_until_fresh_login_is_asked(capture: Capture, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXTURE_PASSWORD", "throwaway-secret")
    capture.figures(figure(box("#welcome"), url="panel.html"), login=LOGIN)
    state = next(capture.state.glob("tester-*.json"))
    first = state.stat().st_mtime_ns
    capture.figures(figure(box("#welcome"), url="panel.html"), login=LOGIN)
    assert state.stat().st_mtime_ns == first
    process = capture.run({"figures": [figure(url="panel.html")], "login": LOGIN}, "--fresh-login")
    assert process.returncode == 0, process.stderr
    assert state.stat().st_mtime_ns > first


def test_failed_login_fails_before_any_figure(capture: Capture, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXTURE_PASSWORD", "wrong")
    message = capture.failure(figure(url="panel.html"), login=LOGIN)
    assert "login expect" in message
    assert not list(capture.state.glob("tester-*.json"))


def test_panel_without_login_shows_denied(capture: Capture) -> None:
    assert "#welcome" in capture.failure(figure(box("#welcome"), url="panel.html"))


def on_user(email: str) -> dict[str, Any]:
    return {"kind": "box", "anchor": {"text": email}}


def test_changed_login_identity_does_not_reuse_the_other_user(capture: Capture) -> None:
    capture.figures(figure(on_user("a@example.com"), url="/account"), login=account_login("a@example.com"))
    capture.figures(figure(on_user("b@example.com"), url="/account"), login=account_login("b@example.com"))


def test_identity_from_environment_does_not_reuse_the_other_user(
    capture: Capture, monkeypatch: pytest.MonkeyPatch
) -> None:
    login = {
        "name": "tester",
        "steps": LOGIN["steps"],
        "expect": {"selector": "#welcome"},
    }
    monkeypatch.setenv("FIXTURE_PASSWORD", "throwaway-secret")
    capture.figures(figure(box("#welcome"), url="panel.html"), login=login)
    monkeypatch.setenv("FIXTURE_PASSWORD", "wrong")
    process = capture.run({"figures": [figure(url="panel.html")], "login": login})
    assert process.returncode == 1
    assert "login expect" in process.stderr


SIGN_OUT = [
    {"action": "click", "target": {"selector": "#signout"}},
    {"action": "wait", "target": {"selector": "#signin"}},
]


def test_dead_session_logs_in_again_on_the_next_run(capture: Capture) -> None:
    login = account_login("a@example.com")
    capture.figures(figure(url="/account", steps=SIGN_OUT), login=login)
    capture.figures(figure(box("#welcome"), url="/account"), login=login)


def test_dead_session_logs_in_again_within_a_run(capture: Capture) -> None:
    login = account_login("a@example.com")
    capture.figures(
        figure(url="/account", steps=SIGN_OUT, slug="leaving"),
        figure(box("#welcome"), url="/account", slug="after"),
        login=login,
    )


def test_session_is_reused_between_figures_and_fresh_login_applies_once(capture: Capture) -> None:
    email = f"{uuid.uuid4().hex}@example.com"
    spec = {
        "figures": [figure(url="/account", slug="first"), figure(url="/account", slug="second")],
        "login": account_login(email),
    }
    process = capture.run(spec, "--fresh-login")
    assert process.returncode == 0, process.stderr
    assert list(SessionHandler.sessions.values()).count(email) == 1


def test_session_that_cannot_be_restored_fails_with_no_picture(capture: Capture) -> None:
    login = {**account_login("a@example.com"), "expect": {"selector": "#absent"}}
    assert "login expect" in capture.failure(figure(url="/account"), login=login)


def test_signed_out_figure_in_a_signed_in_run(capture: Capture) -> None:
    capture.figures(
        figure(box("#signin"), url="/account", slug="outside", login=False),
        figure(box("#welcome"), url="/account", slug="inside"),
        login=account_login("a@example.com"),
    )


def test_all_figures_signed_out_never_log_in(capture: Capture) -> None:
    login = {**account_login("a@example.com"), "expect": {"selector": "#absent"}}
    capture.figures(figure(url="/account", login=False), login=login)


def test_literal_password_is_refused(capture: Capture) -> None:
    login = {
        "name": "tester",
        "steps": [
            {"action": "goto", "url": "login.html"},
            {"action": "fill", "target": {"selector": "#password"}, "value": "throwaway-secret"},
        ],
        "expect": {"selector": "#password"},
    }
    assert "value_env" in capture.failure(figure(url="index.html"), login=login)
    assert not list(capture.out.rglob("spec.json"))


def test_default_state_directory_is_outside_the_project(
    capture: Capture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(Path.home() / ".cache" / "ms-playwright"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.chdir(project)
    spec = tmp_path / "state-spec.json"
    login = account_login("a@example.com")
    spec.write_text(
        json.dumps(
            {
                "environment": "test",
                "base_url": capture.site,
                "login": login,
                "figures": [figure(url="/account")],
            }
        )
    )
    process = run_script("capture.py", str(spec), "--out", str(tmp_path / "out"))
    assert process.returncode == 0, process.stderr
    assert list((tmp_path / "cache" / "preview" / "state").glob("account-*.json"))
    assert not list(project.iterdir())
