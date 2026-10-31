import http.server
import json
import re
import ssl
import subprocess
import threading
import uuid
from collections.abc import Iterator
from functools import partial
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest
from conftest import run_script
from PIL import Image

FIXTURES = Path(__file__).parent / "fixtures"
ACCENT = (230, 0, 126)
REMOVED = (200, 30, 30)
SAVE = {"x": 300, "y": 200, "width": 160, "height": 48}


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *arguments: Any) -> None:
        pass


class SessionHandler(QuietHandler):
    sessions: dict[str, str] = {}

    def token(self) -> str:
        cookies = SimpleCookie(self.headers.get("Cookie", ""))
        return cookies["session"].value if "session" in cookies else ""

    def answer(self, status: int, body: str = "", headers: dict[str, str] | None = None) -> None:
        encoded = body.encode()
        self.send_response(status)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def sign_in(self, query: str) -> None:
        token = uuid.uuid4().hex
        self.sessions[token] = parse_qs(query)["email"][0]
        self.answer(302, headers={"Location": "/account", "Set-Cookie": f"session={token}; Path=/"})

    def sign_out(self) -> None:
        self.sessions.pop(self.token(), None)
        self.answer(302, headers={"Location": "/account"})

    def account(self) -> None:
        email = self.sessions.get(self.token())
        if email is None:
            self.answer(200, '<!doctype html><title>Sign in</title><h1 id="signin">Please sign in</h1>')
            return
        page = f'<!doctype html><title>Account</title><h1 id="welcome">Welcome</h1><p id="user">{email}</p>'
        self.answer(200, page + '<a id="signout" href="/signout">Sign out</a>')

    def do_GET(self) -> None:
        address = urlsplit(self.path)
        if address.path == "/signin":
            self.sign_in(address.query)
        elif address.path == "/signout":
            self.sign_out()
        elif address.path == "/account":
            self.account()
        else:
            super().do_GET()


def serve(wrap: Any = None) -> Iterator[str]:
    handler = partial(SessionHandler, directory=str(FIXTURES))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    scheme = "http"
    if wrap is not None:
        server.socket = wrap(server.socket)
        scheme = "https"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"{scheme}://127.0.0.1:{server.server_address[1]}/"
    server.shutdown()
    server.server_close()
    thread.join()


@pytest.fixture(scope="module")
def site() -> Iterator[str]:
    yield from serve()


@pytest.fixture(scope="module")
def secure_site(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    directory = tmp_path_factory.mktemp("certificate")
    certificate, key = directory / "certificate.pem", directory / "key.pem"
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-subj", "/CN=127.0.0.1",
         "-keyout", str(key), "-out", str(certificate), "-days", "1"],
        check=True,
        capture_output=True,
    )
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certificate, key)
    yield from serve(partial(context.wrap_socket, server_side=True))


class Capture:
    def __init__(self, directory: Path, site: str) -> None:
        self.directory = directory
        self.site = site
        self.out = directory / "out"
        self.state = directory / "state"

    def run(self, spec: dict[str, Any], *flags: str) -> subprocess.CompletedProcess[str]:
        path = self.directory / "spec.json"
        path.write_text(json.dumps({"environment": "test", "base_url": self.site, **spec}))
        return run_script(
            "capture.py", str(path), "--out", str(self.out), "--state-dir", str(self.state),
            "--timeout", "2500", *flags,
        )

    def figures(self, *figures: dict[str, Any], **extra: Any) -> dict[str, Any]:
        process = self.run({"figures": list(figures), **extra})
        assert process.returncode == 0, process.stderr
        return json.loads((self.out / "figures" / "manifest.json").read_text())

    def failure(self, *figures: dict[str, Any], **extra: Any) -> str:
        process = self.run({"figures": list(figures), **extra})
        assert process.returncode == 1, process.stdout
        assert "Traceback" not in process.stderr
        assert not (self.out / "figures" / "manifest.json").exists()
        return process.stderr

    def image(self, name: str) -> Image.Image:
        return Image.open(self.out / "figures" / name).convert("RGB")


@pytest.fixture
def capture(tmp_path: Path, site: str) -> Capture:
    return Capture(tmp_path, site)


def figure(*annotations: dict[str, Any], slug: str = "page", url: str = "index.html", **extra: Any) -> dict[str, Any]:
    return {"slug": slug, "url": url, "annotations": list(annotations), **extra}


def box(selector: str, **extra: Any) -> dict[str, Any]:
    return {"kind": "box", "anchor": {"selector": selector}, **extra}


def near(pixel: tuple[int, int, int], color: tuple[int, int, int], tolerance: int = 40) -> bool:
    return all(abs(left - right) <= tolerance for left, right in zip(pixel, color, strict=True))


def test_box_geometry_matches_element_in_manifest_and_pixels(capture: Capture) -> None:
    manifest = capture.figures(figure(box("#save")))
    mark = manifest["figures"][0]["marks"][0]
    assert mark["element"] == SAVE
    image = capture.image("01-page.png")
    left, top, right, bottom = 296, 196, 464, 252
    middle_x, middle_y = (left + right) // 2, (top + bottom) // 2
    for point in [(left, middle_y), (right, middle_y), (middle_x, top), (middle_x, bottom)]:
        assert near(image.getpixel(point), ACCENT), point
    for point in [(left - 10, middle_y), (right + 10, middle_y), (middle_x, top - 10), (middle_x, bottom + 10)]:
        assert not near(image.getpixel(point), ACCENT), point


def test_page_without_marks_has_no_accent(capture: Capture) -> None:
    capture.figures(figure())
    image = capture.image("01-page.png")
    assert not near(image.getpixel((296, 224)), ACCENT)


def test_box_on_element_far_below_is_drawn_at_document_position(capture: Capture) -> None:
    manifest = capture.figures(figure(box("#far")))
    assert manifest["figures"][0]["marks"][0]["element"]["y"] == 2000
    image = capture.image("01-page.png")
    assert image.height >= 2060
    assert near(image.getpixel((96, 2030)), ACCENT)


def test_viewport_figure_on_a_scrolled_page_keeps_geometry(capture: Capture) -> None:
    manifest = capture.figures(figure(box("#far"), full_page=False))
    assert manifest["figures"][0]["marks"][0]["element"]["y"] == 2000
    image = capture.image("01-page.png")
    assert image.height == 800
    assert any(near(image.getpixel((96, y)), ACCENT) for y in range(800))


def test_retina_scale_keeps_geometry(capture: Capture) -> None:
    capture.figures(figure(box("#save"), viewport={"width": 1280, "height": 800, "scale": 2}))
    image = capture.image("01-page.png")
    assert image.width == 2560
    assert near(image.getpixel((296 * 2, 224 * 2)), ACCENT)


@pytest.mark.parametrize(
    "anchor",
    [{"selector": "#missing"}, {"role": "button", "name": "Nope"}, {"text": "Nope"}, {"selector": "#hidden"}],
)
def test_anchor_miss_fails_and_names_the_anchor(capture: Capture, anchor: dict[str, Any]) -> None:
    message = capture.failure(figure({"kind": "box", "anchor": anchor}))
    assert "matched no visible element" in message
    assert next(iter(anchor.values())) in message


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


def test_ambiguous_anchor_fails(capture: Capture) -> None:
    assert "matched 2 elements" in capture.failure(figure(box(".twin")))


def test_role_and_text_anchors_resolve(capture: Capture) -> None:
    manifest = capture.figures(
        figure(
            {"kind": "box", "anchor": {"role": "button", "name": "Save"}},
            {"kind": "box", "anchor": {"text": "Save"}},
        )
    )
    assert [mark["element"] for mark in manifest["figures"][0]["marks"]] == [SAVE, SAVE]


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


def test_waits_for_animation_before_measuring(capture: Capture) -> None:
    manifest = capture.figures(figure(box("#slide")))
    assert manifest["figures"][0]["marks"][0]["element"]["x"] == 400


def test_endless_animation_does_not_hang_and_is_measured_at_rest(capture: Capture) -> None:
    manifest = capture.figures(figure(box("#spinner")))
    assert manifest["figures"][0]["marks"][0]["element"]["x"] == 700


def test_steps_reach_the_state_that_is_annotated(capture: Capture) -> None:
    steps = [
        {"action": "fill", "target": {"role": "textbox", "name": "Name"}, "value": "Test data"},
        {"action": "click", "target": {"selector": "#apply"}},
        {"action": "wait", "target": {"selector": "#late"}},
        {"action": "press", "key": "Tab"},
        {"action": "wait", "milliseconds": 10},
    ]
    manifest = capture.figures(figure(box("#late"), steps=steps))
    assert manifest["figures"][0]["marks"][0]["element"]["x"] == 640


def test_late_element_without_a_step_still_fails(capture: Capture) -> None:
    assert "#late" in capture.failure(figure(box("#late")))


def test_failing_step_names_its_position(capture: Capture) -> None:
    steps = [{"action": "click", "target": {"selector": "#missing"}}]
    assert "step 1 (click)" in capture.failure(figure(steps=steps))


def test_value_env_missing_fails_without_guessing(capture: Capture) -> None:
    steps = [{"action": "fill", "target": {"selector": "#name"}, "value_env": "PREVIEW_UNSET"}]
    assert "PREVIEW_UNSET" in capture.failure(figure(steps=steps))


def test_error_status_is_not_screenshotted(capture: Capture) -> None:
    assert "404" in capture.failure(figure(url="missing.html"))


def test_inner_panel_is_scrolled_to_the_anchor(capture: Capture) -> None:
    manifest = capture.figures(figure(box("#panel-item")))
    element = manifest["figures"][0]["marks"][0]["element"]
    assert 400 <= element["y"] and element["y"] + element["height"] <= 500


def test_viewport_figure_refuses_anchor_outside_the_viewport(capture: Capture) -> None:
    message = capture.failure(figure(box("#save"), box("#far"), full_page=False))
    assert "outside the viewport" in message


def test_dark_theme_reaches_the_page(capture: Capture) -> None:
    capture.figures(figure(slug="light"), figure(slug="dark", theme="dark"))
    assert near(capture.image("01-light.png").getpixel((5, 700)), (246, 246, 246), 2)
    assert near(capture.image("02-dark.png").getpixel((5, 700)), (16, 16, 16), 2)


def test_overlay_follows_a_positioned_root_element(capture: Capture) -> None:
    manifest = capture.figures(figure(box("#target"), url="shifted.html"))
    element = manifest["figures"][0]["marks"][0]["element"]
    assert (element["x"], element["y"]) == (150, 130)
    image = capture.image("01-page.png")
    assert near(image.getpixel((146, 150)), ACCENT)


def test_label_wider_than_the_page_fails(capture: Capture) -> None:
    annotation = {"kind": "label", "anchor": {"selector": "#save"}, "text": "very long words " * 40}
    assert "wider than the page" in capture.failure(figure(annotation))


def test_every_kind_draws_its_colour(capture: Capture) -> None:
    capture.figures(
        figure(
            {"kind": "arrow", "anchor": {"selector": "#save"}, "offset": {"x": -180, "y": 0}},
            {"kind": "badge", "anchor": {"selector": "#save"}, "number": 1},
            {"kind": "label", "anchor": {"selector": "#save"}, "text": "New"},
        ),
        figure(
            {"kind": "removed", "anchor": {"selector": "#block"}, "offset": {"y": 100}, "text": "Was here"},
            slug="gone",
        ),
    )
    arrow_image = capture.image("01-page.png")
    assert near(arrow_image.getpixel((230, 224)), ACCENT)
    gone = capture.image("02-gone.png")
    edge = [gone.getpixel((x, 596)) for x in range(96, 346)]
    painted = [near(pixel, REMOVED) for pixel in edge]
    assert any(painted) and not all(painted), "removed edge must be dashed"


def test_arrow_tip_touches_the_target_box(capture: Capture) -> None:
    manifest = capture.figures(
        figure({"kind": "arrow", "anchor": {"selector": "#save"}, "offset": {"x": -180, "y": 0}})
    )
    mark = manifest["figures"][0]["marks"][0]
    assert mark["tip"] == {"x": 296, "y": 224}
    assert mark["tail"] == {"x": 200, "y": 224}


def test_arrow_starting_inside_its_target_fails(capture: Capture) -> None:
    annotation = {"kind": "arrow", "anchor": {"selector": "#save"}, "offset": {"x": 5, "y": 0}}
    assert "inside its target" in capture.failure(figure(annotation))


def test_removed_marker_requires_an_offset_from_its_anchor(capture: Capture) -> None:
    annotation = {"kind": "removed", "anchor": {"selector": "#block"}}
    assert "offset" in capture.failure(figure(annotation))


def test_removed_marker_outside_the_page_fails(capture: Capture) -> None:
    annotation = {"kind": "removed", "anchor": {"selector": "#block"}, "offset": {"x": -5000}}
    assert "outside the page" in capture.failure(figure(annotation))


def test_before_url_produces_its_own_preceding_number(capture: Capture, site: str) -> None:
    manifest = capture.figures(
        figure(
            box("#block"),
            before_url=f"{site}old.html",
            before_annotations=[box("#legacy")],
        )
    )
    entries = manifest["figures"]
    assert [(entry["file"], entry["role"]) for entry in entries] == [
        ("figures/01-page-before.png", "before"),
        ("figures/02-page.png", "current"),
    ]
    assert entries[0]["marks"][0]["element"] == {"x": 100, "y": 500, "width": 240, "height": 80}


def test_overlay_does_not_widen_or_lengthen_the_page(capture: Capture) -> None:
    first = capture.figures(figure(slug="plain"))["figures"][0]["page"]
    image = capture.image("01-plain.png")
    assert (image.width, image.height) == (first["width"], first["height"])
    capture.figures(figure(box("#far"), slug="marked"))
    marked = capture.image("01-marked.png")
    assert (marked.width, marked.height) == (image.width, image.height)


def test_too_many_marks_warn(capture: Capture) -> None:
    annotations = [box("#save") for _ in range(6)]
    process = capture.run({"figures": [figure(*annotations)]})
    assert process.returncode == 0, process.stderr
    assert "6 marks" in process.stderr


LOGIN = {
    "name": "tester",
    "steps": [
        {"action": "goto", "url": "login.html"},
        {"action": "fill", "target": {"selector": "#password"}, "value_env": "FIXTURE_PASSWORD"},
        {"action": "click", "target": {"selector": "#enter"}},
    ],
    "expect": {"selector": "#welcome"},
}


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


@pytest.mark.parametrize("environment", ["production", "PROD", "live"])
def test_production_is_refused(capture: Capture, environment: str) -> None:
    process = capture.run({"environment": environment, "figures": [figure()]})
    assert process.returncode == 1
    assert "refusing" in process.stderr


@pytest.mark.parametrize(
    ("change", "fragment"),
    [
        ({"environment": ""}, "environment"),
        ({"base_url": ""}, "base_url"),
        ({"figures": []}, "figures"),
        ({"figures": [{"slug": "Bad Slug", "url": "x"}]}, "slug"),
        ({"figures": [figure({"kind": "circle", "anchor": {"selector": "a"}})]}, "circle"),
        ({"figures": [figure({"kind": "box"})]}, "anchor"),
        ({"figures": [figure({"kind": "box", "anchor": {"selector": "a", "text": "b"}})]}, "exactly one"),
        ({"figures": [figure(steps=[{"action": "dance"}])]}, "dance"),
        ({"figures": [figure(theme="sepia")]}, "theme"),
        ({"figures": [figure()], "login": {"name": "x", "steps": [{"action": "wait", "milliseconds": 1}]}}, "expect"),
    ],
)
def test_invalid_spec_is_refused(capture: Capture, change: dict[str, Any], fragment: str) -> None:
    process = capture.run({"figures": [figure()], **change})
    assert process.returncode == 1
    assert "Traceback" not in process.stderr
    assert fragment in process.stderr


def test_documented_spec_example_is_valid(capture: Capture) -> None:
    reference = Path(__file__).parent.parent / "skills/preview/references/capture-spec.md"
    example = json.loads(re.search(r"## Spec\n\n```json\n(.*?)```", reference.read_text(), re.DOTALL)[1])
    del example["login"], example["base_url"]
    message = capture.failure(*example["figures"])
    assert "answered with status 404" in message


def test_self_signed_certificate_needs_the_flag(tmp_path: Path, secure_site: str) -> None:
    capture = Capture(tmp_path, secure_site)
    process = capture.run({"figures": [figure(box("#save"))]})
    assert process.returncode == 1
    assert "ERR_CERT" in process.stderr
    process = capture.run({"figures": [figure(box("#save"))]}, "--ignore-https-errors")
    assert process.returncode == 0, process.stderr


def account_login(email: str) -> dict[str, Any]:
    return {
        "name": "account",
        "steps": [{"action": "goto", "url": f"/signin?email={email}"}],
        "expect": {"selector": "#welcome"},
    }


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


SIGN_OUT = [{"action": "click", "target": {"selector": "#signout"}}, {"action": "wait", "target": {"selector": "#signin"}}]


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


def test_hover_step_reaches_the_hover_state(capture: Capture) -> None:
    steps = [{"action": "hover", "target": {"selector": "#hover-target"}}]
    capture.figures(figure(box("#tip"), url="extras.html", steps=steps))


@pytest.mark.parametrize(
    ("field", "anchor"),
    [("has_touch", "#touch"), ("reduced_motion", "#reduced")],
)
def test_device_flags_reach_the_page(capture: Capture, field: str, anchor: str) -> None:
    assert anchor in capture.failure(figure(box(anchor), url="extras.html"))
    capture.figures(figure(box(anchor), url="extras.html", **{field: True}))


def test_signed_out_figure_in_a_signed_in_run(capture: Capture) -> None:
    capture.figures(
        figure(box("#signin"), url="/account", slug="outside", login=False),
        figure(box("#welcome"), url="/account", slug="inside"),
        login=account_login("a@example.com"),
    )


def test_all_figures_signed_out_never_log_in(capture: Capture) -> None:
    login = {**account_login("a@example.com"), "expect": {"selector": "#absent"}}
    capture.figures(figure(url="/account", login=False), login=login)


def test_badge_outside_leaves_the_corner_free(capture: Capture) -> None:
    annotation = {
        "kind": "badge", "anchor": {"selector": "#tight"}, "number": 1, "placement": "left",
    }
    manifest = capture.figures(figure(annotation, url="extras.html"))
    center = manifest["figures"][0]["marks"][0]["badge"]
    assert center == {"x": 376, "y": 412}
    image = capture.image("01-page.png")
    assert near(image.getpixel((370, 412)), ACCENT)
    assert not near(image.getpixel((402, 402)), ACCENT)


@pytest.mark.parametrize(
    ("placement", "center"),
    [("corner", (396, 396)), ("right", (524, 412)), ("above", (450, 376)), ("below", (450, 448))],
)
def test_badge_placements(capture: Capture, placement: str, center: tuple[int, int]) -> None:
    annotation = {
        "kind": "badge", "anchor": {"selector": "#tight"}, "number": 1, "placement": placement,
    }
    manifest = capture.figures(figure(annotation, url="extras.html"))
    badge = manifest["figures"][0]["marks"][0]["badge"]
    assert (badge["x"], badge["y"]) == center


def test_badge_placed_outside_the_page_fails(capture: Capture) -> None:
    annotation = {"kind": "badge", "anchor": {"selector": "header"}, "number": 1, "placement": "above"}
    assert "outside the page" in capture.failure(figure(annotation))


def test_unknown_placement_is_refused(capture: Capture) -> None:
    annotation = {"kind": "badge", "anchor": {"selector": "#save"}, "number": 1, "placement": "middle"}
    assert "placement" in capture.failure(figure(annotation))


PORTAL_PIXEL = (20, 780)


def test_dev_overlay_in_a_shadow_root_shows_by_default(capture: Capture) -> None:
    capture.figures(figure(url="extras.html"))
    assert near(capture.image("01-page.png").getpixel(PORTAL_PIXEL), (255, 0, 0), 2)


@pytest.mark.parametrize("selector", ["nextjs-portal", "#shadow-inner"])
def test_hide_removes_overlay_host_or_shadow_content(capture: Capture, selector: str) -> None:
    capture.figures(figure(url="extras.html"), hide=[selector, "#not-on-this-page"])
    assert near(capture.image("01-page.png").getpixel(PORTAL_PIXEL), (255, 255, 255), 2)


def test_invalid_hide_is_refused(capture: Capture) -> None:
    assert "hide" in capture.failure(figure(), hide="nextjs-portal")


@pytest.mark.parametrize(
    "anchor",
    [
        {"text": "another task", "match": "substring"},
        {"text": "^Add .* task$", "match": "regex"},
        {"role": "button", "name": "another", "match": "substring"},
        {"role": "button", "name": "^Add", "match": "regex"},
    ],
)
def test_text_matching_modes_find_the_element(capture: Capture, anchor: dict[str, Any]) -> None:
    capture.figures(figure({"kind": "box", "anchor": anchor}, url="extras.html"))


def test_text_is_exact_by_default(capture: Capture) -> None:
    annotation = {"kind": "box", "anchor": {"text": "another task"}}
    assert "matched no visible" in capture.failure(figure(annotation, url="extras.html"))


@pytest.mark.parametrize(
    "anchor",
    [{"text": "x", "match": "fuzzy"}, {"text": "(", "match": "regex"}, {"selector": "a", "match": "regex"}],
)
def test_invalid_match_is_refused(capture: Capture, anchor: dict[str, Any]) -> None:
    assert "match" in capture.failure(figure({"kind": "box", "anchor": anchor}))


def test_spec_is_saved_beside_the_figures_without_secrets(
    capture: Capture, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    spec.write_text(json.dumps({
        "environment": "test", "base_url": capture.site, "login": login, "figures": [figure(url="/account")],
    }))
    process = run_script("capture.py", str(spec), "--out", str(tmp_path / "out"))
    assert process.returncode == 0, process.stderr
    assert list((tmp_path / "cache" / "preview" / "state").glob("account-*.json"))
    assert not list(project.iterdir())


ROOMY_CENTERS = {
    "top-left": (596, 96),
    "corner": (596, 96),
    "top-right": (804, 96),
    "bottom-left": (596, 204),
    "bottom-right": (804, 204),
    "inside": (614, 114),
}


def numbered(placement: str | None = None, kind: str = "badge", anchor: str = "#roomy") -> dict[str, Any]:
    mark: dict[str, Any] = {"kind": kind, "anchor": {"selector": anchor}, "number": 1}
    return mark | ({"placement": placement} if placement else {})


def badge_at(capture: Capture, center: tuple[int, int], name: str = "01-page.png") -> bool:
    return near(capture.image(name).getpixel((center[0] - 10, center[1])), ACCENT)


@pytest.mark.parametrize(("placement", "center"), ROOMY_CENTERS.items())
@pytest.mark.parametrize("kind", ["badge", "box"])
def test_number_sits_at_each_placement(capture: Capture, kind: str, placement: str, center: tuple[int, int]) -> None:
    manifest = capture.figures(figure(numbered(placement, kind), url="extras.html"))
    badge = manifest["figures"][0]["marks"][0]["badge"]
    assert (badge["x"], badge["y"]) == center
    assert badge_at(capture, center)
    if kind == "badge":
        for other in set(ROOMY_CENTERS.values()) - {center}:
            assert not badge_at(capture, other), other


def test_inside_keeps_the_whole_number_in_the_shape(capture: Capture) -> None:
    capture.figures(figure(numbered("inside"), url="extras.html"))
    image = capture.image("01-page.png")
    for x in range(590, 600):
        assert not near(image.getpixel((x, 114)), ACCENT)
    for y in range(90, 100):
        assert not near(image.getpixel((614, y)), ACCENT)


def test_inside_too_small_for_the_number_fails(capture: Capture) -> None:
    message = capture.failure(figure(numbered("inside", anchor="#tight"), url="extras.html"))
    assert "too small" in message


def test_placement_without_a_number_is_not_checked(capture: Capture) -> None:
    capture.figures(figure(box("#tight"), url="extras.html", placement="inside"))


@pytest.mark.parametrize(
    ("spec_level", "figure_level", "annotation_level", "expected"),
    [
        (None, None, None, "corner"),
        ("top-right", None, None, "top-right"),
        ("top-right", "bottom-left", None, "bottom-left"),
        ("top-right", "bottom-left", "inside", "inside"),
        (None, "bottom-right", None, "bottom-right"),
    ],
)
def test_default_chain(
    capture: Capture, spec_level: str | None, figure_level: str | None, annotation_level: str | None, expected: str
) -> None:
    levels = {"placement": figure_level} if figure_level else {}
    extra = {"placement": spec_level} if spec_level else {}
    manifest = capture.figures(figure(numbered(annotation_level), url="extras.html", **levels), **extra)
    center = ROOMY_CENTERS[expected]
    badge = manifest["figures"][0]["marks"][0]["badge"]
    assert (badge["x"], badge["y"]) == center
    assert badge_at(capture, center)


def test_before_marks_inherit_the_figure_placement(capture: Capture, site: str) -> None:
    annotation = {"kind": "box", "anchor": {"selector": "#legacy"}, "number": 1}
    manifest = capture.figures(
        figure(url="index.html", before_url=f"{site}old.html", before_annotations=[annotation], placement="top-right")
    )
    badge = manifest["figures"][0]["marks"][0]["badge"]
    assert (badge["x"], badge["y"]) == (344, 496)


@pytest.mark.parametrize(
    ("build", "level"),
    [
        (lambda: {"figures": [figure()], "placement": "middle"}, "spec:"),
        (lambda: {"figures": [figure(placement="middle")]}, "figure 1"),
        (lambda: {"figures": [figure(numbered("middle"))]}, "annotation 1"),
    ],
    ids=["spec", "figure", "annotation"],
)
def test_invalid_placement_names_its_level(capture: Capture, build: Any, level: str) -> None:
    process = capture.run(build())
    assert process.returncode == 1
    assert level in process.stderr
    assert "placement" in process.stderr


@pytest.mark.parametrize("placement", ["inside", "top-right", "bottom-left", "bottom-right"])
def test_explicit_arrow_placement_that_makes_no_sense_fails(capture: Capture, placement: str) -> None:
    assert "does not apply to an arrow" in capture.failure(figure(numbered(placement, "arrow")))


@pytest.mark.parametrize("placement", ["corner", "top-left"])
def test_arrow_number_sits_on_its_tail(capture: Capture, placement: str) -> None:
    annotation = numbered(placement, "arrow", "#save") | {"offset": {"x": -180, "y": 0}}
    badge = capture.figures(figure(annotation))["figures"][0]["marks"][0]["badge"]
    assert badge == {"x": 200, "y": 224}


def test_inherited_placement_an_arrow_cannot_use_falls_back_to_its_tail(capture: Capture) -> None:
    annotation = numbered(None, "arrow", "#save") | {"offset": {"x": -180, "y": 0}}
    badge = capture.figures(figure(annotation, placement="inside"))["figures"][0]["marks"][0]["badge"]
    assert badge == {"x": 200, "y": 224}


def test_arrow_keeps_outside_placements(capture: Capture) -> None:
    annotation = numbered("right", "arrow", "#save") | {"offset": {"x": -180, "y": 0}}
    badge = capture.figures(figure(annotation))["figures"][0]["marks"][0]["badge"]
    assert badge == {"x": 484, "y": 224}


def test_explicit_corner_renders_exactly_like_the_default(capture: Capture) -> None:
    capture.figures(figure(numbered(), url="extras.html", slug="plain"), figure(numbered("corner"), url="extras.html", slug="named"))
    assert capture.image("01-plain.png").tobytes() == capture.image("02-named.png").tobytes()


def test_saved_spec_keeps_placement_fields_as_given(capture: Capture) -> None:
    capture.figures(figure(numbered(), url="extras.html", placement="inside"), placement="top-right")
    saved = json.loads((capture.out / "figures" / "spec.json").read_text())
    assert saved["placement"] == "top-right"
    assert saved["figures"][0]["placement"] == "inside"
    assert "placement" not in saved["figures"][0]["annotations"][0]
