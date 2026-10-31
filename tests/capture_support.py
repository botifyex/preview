import http.server
import json
import subprocess
import threading
import uuid
from collections.abc import Iterator
from functools import partial
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any, ClassVar, cast, override
from urllib.parse import parse_qs, urlsplit

from PIL import Image
from support import run_script

FIXTURES = Path(__file__).parent / "fixtures"


ACCENT = (230, 0, 126)


REMOVED = (200, 30, 30)


type Pixel = float | tuple[int, ...] | None


SAVE = {"x": 300, "y": 200, "width": 160, "height": 48}


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    @override
    def log_message(self, format: str, *arguments: Any) -> None:
        pass


class SessionHandler(QuietHandler):
    sessions: ClassVar[dict[str, str]] = {}

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

    @override
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


class Capture:
    def __init__(self, directory: Path, site: str) -> None:
        self.directory: Path = directory
        self.site: str = site
        self.out: Path = directory / "out"
        self.state: Path = directory / "state"

    def run(self, spec: dict[str, Any], *flags: str) -> subprocess.CompletedProcess[str]:
        path = self.directory / "spec.json"
        path.write_text(json.dumps({"environment": "test", "base_url": self.site, **spec}))
        return run_script(
            "capture.py",
            str(path),
            "--out",
            str(self.out),
            "--state-dir",
            str(self.state),
            "--timeout",
            "2500",
            *flags,
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


def figure(*annotations: dict[str, Any], slug: str = "page", url: str = "index.html", **extra: Any) -> dict[str, Any]:
    return {"slug": slug, "url": url, "annotations": list(annotations), **extra}


def box(selector: str, **extra: Any) -> dict[str, Any]:
    return {"kind": "box", "anchor": {"selector": selector}, **extra}


def near(pixel: Pixel, color: tuple[int, int, int], tolerance: int = 40) -> bool:
    channels = cast("tuple[int, int, int]", pixel)
    return all(abs(left - right) <= tolerance for left, right in zip(channels, color, strict=True))


LOGIN = {
    "name": "tester",
    "steps": [
        {"action": "goto", "url": "login.html"},
        {"action": "fill", "target": {"selector": "#password"}, "value_env": "FIXTURE_PASSWORD"},
        {"action": "click", "target": {"selector": "#enter"}},
    ],
    "expect": {"selector": "#welcome"},
}


def account_login(email: str) -> dict[str, Any]:
    return {
        "name": "account",
        "steps": [{"action": "goto", "url": f"/signin?email={email}"}],
        "expect": {"selector": "#welcome"},
    }
