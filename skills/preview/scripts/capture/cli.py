import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, sync_playwright
from playwright.sync_api import Error as PlaywrightError

from capture.constants import FAILURES_NAME, PLAYWRIGHT_VERSION
from capture.model import CaptureFailure, Options, Spec, first_line
from capture.publish import publish, refuse_conflicts
from capture.shots import capture_all, planned_names
from capture.validation import read_spec, validate_spec


def launch(playwright: Any) -> Browser:
    try:
        return playwright.chromium.launch()
    except PlaywrightError as failure:
        raise CaptureFailure(
            f"cannot start Chromium, try: uv run --with playwright=={PLAYWRIGHT_VERSION} playwright install chromium"
        ) from failure


def run(spec_path: Path, options: Options) -> list[Spec]:
    spec = read_spec(spec_path)
    validate_spec(spec)
    refuse_conflicts(planned_names(spec), options.output / "figures")
    options.output.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(options.output / FAILURES_NAME, ignore_errors=True)
    with tempfile.TemporaryDirectory(dir=options.output, prefix=".capture-") as directory:
        staging = Path(directory)
        with sync_playwright() as playwright:
            browser = launch(playwright)
            try:
                entries = capture_all(browser, spec, options, staging)
            except PlaywrightError as failure:
                raise CaptureFailure(first_line(failure)) from failure
            finally:
                browser.close()
        publish(staging, options.output / "figures", entries, spec)
    return entries


def default_state_directory() -> Path:
    cache = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(cache) / "preview" / "state"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Capture annotated screenshots from a JSON spec")
    result.add_argument("spec", type=Path)
    result.add_argument("--out", type=Path, required=True)
    result.add_argument("--state-dir", type=Path, default=default_state_directory())
    result.add_argument("--ignore-https-errors", action="store_true")
    result.add_argument("--fresh-login", action="store_true")
    result.add_argument("--timeout", type=int, default=10000)
    return result


def main() -> int:
    arguments = parser().parse_args()
    options = Options(
        arguments.out, arguments.state_dir, arguments.ignore_https_errors, arguments.fresh_login, arguments.timeout
    )
    try:
        entries = run(arguments.spec, options)
    except (CaptureFailure, OSError) as failure:
        print(f"error: {failure}", file=sys.stderr)
        return 1
    for entry in entries:
        print(entry["file"])
        for warning in entry["warnings"]:
            print(f"warning: {entry['file']}: {warning}", file=sys.stderr)
    return 0
