from pathlib import Path

import pytest
from support import run_script

FIGURE_ONE = "figures/01-export.png"
FIGURE_TWO = "figures/02-menu.png"
GOOD = f"""![Figure 1]({FIGURE_ONE})
**1.** The export button

![Figure 2]({FIGURE_TWO})
**2.** The new menu

# What is new in version 2

## Main changes

You can now export a report ([figure 1]({FIGURE_ONE})).

## Other changes

The menu moved ([figure 2]({FIGURE_TWO})). Small fixes.
"""


def report_directory(root: Path, text: str, files: tuple[str, ...] = (FIGURE_ONE, FIGURE_TWO)) -> Path:
    (root / "figures").mkdir(exist_ok=True)
    for name in files:
        (root / name).write_bytes(b"image")
    (root / "RELEASE.md").write_text(text)
    return root


def checked(directory: Path) -> tuple[int, str]:
    process = run_script("check_report.py", str(directory))
    return process.returncode, process.stderr


def test_good_report_passes(tmp_path: Path) -> None:
    assert checked(report_directory(tmp_path, GOOD)) == (0, "")


def test_translated_headings_pass(tmp_path: Path) -> None:
    text = GOOD.replace("Main changes", "Главное").replace("Other changes", "Остальное")
    assert checked(report_directory(tmp_path, text))[0] == 0


def test_heading_inside_code_fence_is_not_a_section(tmp_path: Path) -> None:
    text = GOOD + "\n```\n# not a heading\n## neither\n```\n"
    assert checked(report_directory(tmp_path, text))[0] == 0


def test_manifest_on_disk_is_not_a_figure(tmp_path: Path) -> None:
    directory = report_directory(tmp_path, GOOD)
    (directory / "figures" / "manifest.json").write_text("{}")
    assert checked(directory)[0] == 0


SWAPPED = GOOD.replace("# What is new in version 2\n\n", "").replace(
    f"![Figure 1]({FIGURE_ONE})", f"# What is new in version 2\n\n![Figure 1]({FIGURE_ONE})"
)
IMAGE_AFTER_TITLE = GOOD.replace(f"![Figure 2]({FIGURE_TWO})\n**2.** The new menu\n\n", "").replace(
    "## Main changes", f"![Figure 2]({FIGURE_TWO})\n\n## Main changes"
)
TEXT_FIRST = "Intro words\n\n" + GOOD
NO_TITLE = GOOD.replace("# What is new in version 2\n\n", "")
NO_OTHER = GOOD[: GOOD.index("## Other changes")]
OTHER_ONLY_REFERS = GOOD.replace(f"([figure 1]({FIGURE_ONE}))", "").replace(
    "Small fixes.", f"Small fixes ([figure 1]({FIGURE_ONE}))."
)
NEVER_REFERENCED = GOOD.replace(f"([figure 2]({FIGURE_TWO}))", "")
GAP = GOOD.replace("02-menu", "03-menu")
OUT_OF_ORDER_ONE = "figures/02-export.png"
OUT_OF_ORDER_TWO = "figures/01-menu.png"
REVERSED = GOOD.replace(FIGURE_ONE, OUT_OF_ORDER_ONE).replace(FIGURE_TWO, OUT_OF_ORDER_TWO)
BAD_NAME = GOOD.replace("01-export", "export")
GHOST_LINK = GOOD.replace("Small fixes.", "See ([figure 9](figures/09-ghost.png)).")
NOT_EMBEDDED_LINK = GOOD.replace("Small fixes.", "See ([figure 3](figures/03-extra.png)).")


@pytest.mark.parametrize(
    ("text", "files", "code"),
    [
        pytest.param(TEXT_FIRST, (FIGURE_ONE, FIGURE_TWO), "images-first", id="text-before-images"),
        pytest.param(SWAPPED, (FIGURE_ONE, FIGURE_TWO), "images-first", id="title-before-images"),
        pytest.param(IMAGE_AFTER_TITLE, (FIGURE_ONE, FIGURE_TWO), "images-first", id="image-after-title"),
        pytest.param(NO_TITLE, (FIGURE_ONE, FIGURE_TWO), "section-order", id="no-title"),
        pytest.param(NO_OTHER, (FIGURE_ONE,), "section-order", id="no-other-section"),
        pytest.param(GOOD + "\n## Third\n", (FIGURE_ONE, FIGURE_TWO), "section-order", id="third-section"),
        pytest.param(NEVER_REFERENCED, (FIGURE_ONE, FIGURE_TWO), "unreferenced-figure", id="figure-unreferenced"),
        pytest.param(
            GOOD, (FIGURE_ONE, FIGURE_TWO, "figures/03-extra.png"), "unreferenced-figure", id="file-not-in-report"
        ),
        pytest.param(GOOD, (FIGURE_ONE,), "missing-file", id="file-missing"),
        pytest.param(GHOST_LINK, (FIGURE_ONE, FIGURE_TWO), "missing-file", id="reference-without-file"),
        pytest.param(
            NOT_EMBEDDED_LINK, (FIGURE_ONE, FIGURE_TWO, "figures/03-extra.png"), "missing-file", id="link-not-embedded"
        ),
        pytest.param(GAP, (FIGURE_ONE, "figures/03-menu.png"), "numbering", id="numbering-gap"),
        pytest.param(REVERSED, (OUT_OF_ORDER_ONE, OUT_OF_ORDER_TWO), "numbering", id="numbering-reversed"),
        pytest.param(BAD_NAME, ("figures/export.png", FIGURE_TWO), "numbering", id="bad-name"),
        pytest.param(OTHER_ONLY_REFERS, (FIGURE_ONE, FIGURE_TWO), "main-without-figure", id="main-without-figure"),
    ],
)
def test_broken_report_fails_for_the_named_reason(tmp_path: Path, text: str, files: tuple[str, ...], code: str) -> None:
    returncode, errors = checked(report_directory(tmp_path, text, files))
    assert returncode == 1
    assert [line for line in errors.splitlines() if line.startswith(f"{code}:")], errors


def test_missing_report_fails(tmp_path: Path) -> None:
    returncode, errors = checked(tmp_path)
    assert returncode == 1
    assert errors.startswith("missing-report:")


def test_report_without_any_figure_fails(tmp_path: Path) -> None:
    returncode, errors = checked(report_directory(tmp_path, "# Title\n\n## Main\n\nWords\n\n## Other\n\nWords\n", ()))
    assert returncode == 1
    assert "images-first" in errors and "main-without-figure" in errors
