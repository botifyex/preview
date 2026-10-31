from pathlib import Path

from playwright.sync_api import Browser

from capture.model import Options, Spec
from capture.scheme.composite import capture_scheme
from capture.shots import Logins, all_shots, capture_shot


def capture_all(browser: Browser, spec: Spec, options: Options, staging: Path) -> list[Spec]:
    logins = Logins(browser, spec, options, options.fresh_login)
    entries: list[Spec] = []
    for number, shot in enumerate(all_shots(spec), 1):
        if shot.role == "scheme":
            entries.append(capture_scheme(browser, spec, shot, number, options, logins, staging))
        else:
            entries.append(capture_shot(browser, spec, shot, number, options, logins.state(shot), staging))
    return entries
