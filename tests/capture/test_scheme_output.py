import json

from helpers import Capture, figure
from scheme_helpers import YELLOW, panel, scheme, three
from support import run_script

GOOD = (figure(slug="first"), three(slug="path", links="sequence"))
BROKEN_MIDDLE = scheme(panel(), panel(YELLOW, steps=[{"action": "click", "target": {"selector": "#ghost"}}]), panel())


def snapshot(capture: Capture) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in (capture.out / "figures").iterdir()}


def test_numbering_runs_across_figures_and_schemes(capture: Capture) -> None:
    before = figure(slug="old", before_url="index.html")
    manifest = capture.figures(figure(slug="first"), three(slug="path"), before, three(slug="last"))
    names = [entry["file"] for entry in manifest["figures"]]
    assert names == [
        "figures/01-first.png",
        "figures/02-path.png",
        "figures/03-old-before.png",
        "figures/04-old.png",
        "figures/05-last.png",
    ]
    assert [entry["number"] for entry in manifest["figures"]] == [1, 2, 3, 4, 5]
    assert [entry["role"] for entry in manifest["figures"]] == ["current", "scheme", "before", "current", "scheme"]
    on_disk = sorted(path.name for path in (capture.out / "figures").glob("*.png"))
    assert on_disk == [name.removeprefix("figures/") for name in names]


def test_failure_in_the_middle_panel_leaves_earlier_output(capture: Capture) -> None:
    capture.figures(*GOOD)
    earlier = snapshot(capture)
    process = capture.run({"figures": [figure(slug="first"), BROKEN_MIDDLE]})
    assert process.returncode == 1
    assert "error: figure scheme panel 2 step 1 (click)" in process.stderr
    assert "Traceback" not in process.stderr
    assert snapshot(capture) == earlier
    assert sorted(path.name for path in capture.out.iterdir()) == ["failures", "figures"]
    assert [path.name for path in (capture.out / "failures").iterdir()] == ["scheme-panel-2.png"]


def test_a_failure_in_the_panel_page_names_the_panel(capture: Capture) -> None:
    stderr = capture.failure(scheme(panel(), {"url": "missing.html"}))
    assert "error: figure scheme panel 2: " in stderr
    assert "missing.html answered with status 404" in stderr


def test_failure_on_a_first_run_leaves_no_figures(capture: Capture) -> None:
    capture.failure(BROKEN_MIDDLE)
    assert not (capture.out / "figures").exists()
    assert sorted(path.name for path in capture.out.iterdir()) == ["failures"]


def test_success_leaves_no_panel_files(capture: Capture) -> None:
    capture.figures(three())
    assert sorted(path.name for path in capture.out.iterdir()) == ["figures"]


def test_conflict_with_a_foreign_file_is_refused_before_capture(capture: Capture) -> None:
    figures = capture.out / "figures"
    figures.mkdir(parents=True)
    (figures / "01-scheme.png").write_text("mine")
    process = capture.run({"figures": [three()]})
    assert process.returncode == 1
    assert "01-scheme.png already exists and was not created by this tool" in process.stderr
    assert (figures / "01-scheme.png").read_text() == "mine"


def test_second_run_replaces_a_scheme_it_owns(capture: Capture) -> None:
    capture.figures(three())
    capture.figures(three(layout="column"))
    manifest = json.loads((capture.out / "figures" / "manifest.json").read_text())
    assert manifest["figures"][0]["layout"] == "column"


REPORT = """![Figure 1: the page](figures/01-first.png)
**1.** The page

![Figure 2: the path](figures/02-path.png)
**2.** The path to the result

# What is new

You can reach the result in three steps.

## Main changes

Start on the page ([figure 1](figures/01-first.png)), then follow the path
([figure 2](figures/02-path.png)).

## Other changes

- Nothing else.
"""


def test_check_report_accepts_a_scheme(capture: Capture) -> None:
    capture.figures(*GOOD)
    (capture.out / "RELEASE.md").write_text(REPORT)
    process = run_script("check_report.py", str(capture.out))
    assert process.returncode == 0, process.stderr
    assert process.stdout.strip() == "ok"


def test_check_report_still_wants_a_scheme_referenced(capture: Capture) -> None:
    capture.figures(*GOOD)
    (capture.out / "RELEASE.md").write_text(REPORT.replace("([figure 2](figures/02-path.png))", ""))
    process = run_script("check_report.py", str(capture.out))
    assert process.returncode == 1
    assert "unreferenced-figure: figures/02-path.png" in process.stderr


def test_saved_spec_repeats_a_scheme(capture: Capture) -> None:
    capture.figures(*GOOD)
    saved = capture.out / "figures" / "spec.json"
    process = run_script("run_capture.py", str(saved), "--out", str(capture.out), "--state-dir", str(capture.state))
    assert process.returncode == 0, process.stderr
    assert "figures/02-path.png" in process.stdout
