#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
from collections.abc import Generator
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import override

SHOWCASE = Path(__file__).resolve().parent
SCRIPTS = SHOWCASE.parent.parent / "skills" / "preview" / "scripts"
SPEC = SHOWCASE / "spec.json"
REPORT_NAME = "RELEASE.md"
LOGIN_VARIABLE = "SHOWCASE_PASSWORD"
LOCAL_HOST = "127.0.0.1"


class BuildFailure(Exception):
    pass


class QuietHandler(SimpleHTTPRequestHandler):
    @override
    def log_message(self, format: str, *args: object) -> None:
        pass


@contextmanager
def serving(directory: Path) -> Generator[str]:
    handler = partial(QuietHandler, directory=str(directory))
    server = ThreadingHTTPServer((LOCAL_HOST, 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://{LOCAL_HOST}:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def committed_base_url() -> str:
    return json.loads(SPEC.read_text())["base_url"]


def write_resolved_spec(path: Path, base_url: str) -> None:
    path.write_text(SPEC.read_text().replace(committed_base_url(), base_url))


def run_script(name: str, *arguments: str, environment: dict[str, str] | None = None) -> None:
    command = ["uv", "run", "--quiet", str(SCRIPTS / name), *arguments]
    process = subprocess.run(command, env=environment, check=False)
    if process.returncode != 0:
        raise BuildFailure(f"{name} exited with {process.returncode}")


def restore_base_url(figures: Path, base_url: str) -> None:
    for name in ("manifest.json", "spec.json"):
        path = figures / name
        path.write_text(path.read_text().replace(base_url, committed_base_url()))


def capture(output: Path, scratch: Path) -> None:
    resolved = scratch / "spec.json"
    with serving(SHOWCASE / "site") as base_url:
        write_resolved_spec(resolved, base_url)
        environment = {**os.environ, LOGIN_VARIABLE: secrets.token_urlsafe(16)}
        run_script(
            "run_capture.py",
            str(resolved),
            "--out",
            str(output),
            "--state-dir",
            str(scratch / "state"),
            environment=environment,
        )
    restore_base_url(output / "figures", base_url)


def copy_report(output: Path) -> None:
    if output != SHOWCASE:
        shutil.copy(SHOWCASE / REPORT_NAME, output / REPORT_NAME)


def build(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="showcase-") as scratch:
        capture(output, Path(scratch))
    copy_report(output)
    run_script("check_report.py", str(output))


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild the showcase figures from spec.json and check the report")
    parser.add_argument("--out", type=Path, default=SHOWCASE, help="directory for figures/ and the report copy")
    arguments = parser.parse_args()
    try:
        build(arguments.out.resolve())
    except BuildFailure as failure:
        print(f"error: {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
