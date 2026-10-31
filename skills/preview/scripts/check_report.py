#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
import argparse
import re
import sys
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import override


class Code(StrEnum):
    MISSING_REPORT = "missing-report"
    IMAGES_FIRST = "images-first"
    SECTION_ORDER = "section-order"
    UNREFERENCED_FIGURE = "unreferenced-figure"
    MISSING_FILE = "missing-file"
    NUMBERING = "numbering"
    MAIN_WITHOUT_FIGURE = "main-without-figure"


REPORT_NAME = "RELEASE.md"
FIGURE_DIRECTORY = "figures"
FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^(#{1,6})\s+\S")
IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)[^)]*\)")
REFERENCE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)[^)]*\)")
FIGURE_NAME = re.compile(r"(\d{2,})-[^/]+\.png")
SECTION_LEVEL = 2


@dataclass(frozen=True)
class Problem:
    code: Code
    message: str

    @override
    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


@dataclass
class Sections:
    opening: list[str] = field(default_factory=list)
    title: list[str] = field(default_factory=list)
    main: list[str] = field(default_factory=list)
    other: list[str] = field(default_factory=list)
    headings: list[int] = field(default_factory=list)

    @property
    def body(self) -> list[str]:
        return self.title + self.main + self.other


def without_fences(lines: list[str]) -> list[str]:
    kept: list[str] = []
    inside = False
    for line in lines:
        if FENCE.match(line):
            inside = not inside
        elif not inside:
            kept.append(line)
    return kept


def split_sections(lines: list[str]) -> Sections:
    sections = Sections()
    current = sections.opening
    targets = [sections.main, sections.other]
    for line in lines:
        match = HEADING.match(line)
        level = len(match[1]) if match else 0
        if level in (1, SECTION_LEVEL):
            sections.headings.append(level)
        if level == 1 and current is sections.opening:
            current = sections.title
        elif level == SECTION_LEVEL and targets:
            current = targets.pop(0)
        current.append(line)
    return sections


def is_figure(target: str) -> bool:
    return target.startswith(f"{FIGURE_DIRECTORY}/")


def images_in(lines: list[str]) -> list[str]:
    return [target for line in lines for target in IMAGE.findall(line) if is_figure(target)]


def references_in(lines: list[str]) -> list[str]:
    return [target for line in lines for target in REFERENCE.findall(line) if is_figure(target)]


def check_opening(sections: Sections) -> list[Problem]:
    filled = [line for line in sections.opening if line.strip()]
    if not filled or not IMAGE.search(filled[0]):
        return [Problem(Code.IMAGES_FIRST, "the report must open with the figures, before anything else")]
    late = images_in(sections.body)
    if late:
        return [Problem(Code.IMAGES_FIRST, f"{late[0]} is embedded after the title, all figures go first")]
    return []


def check_order(sections: Sections) -> list[Problem]:
    if sections.headings != [1, 2, 2]:
        shape = " ".join("#" * level for level in sections.headings) or "none"
        message = f"expected one title then two sections (# ## ##), found: {shape}"
        return [Problem(Code.SECTION_ORDER, message)]
    return []


def check_numbering(images: list[str]) -> list[Problem]:
    matches = [FIGURE_NAME.fullmatch(Path(image).name) for image in images]
    bad = [image for image, match in zip(images, matches, strict=True) if match is None]
    if bad:
        return [Problem(Code.NUMBERING, f"{bad[0]} is not named NN-slug.png")]
    numbers = [int(match[1]) for match in matches if match]
    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        return [Problem(Code.NUMBERING, f"figures are numbered {numbers}, expected {expected}")]
    return []


def check_files(targets: list[str], directory: Path) -> list[Problem]:
    missing = sorted({target for target in targets if not (directory / target).is_file()})
    return [Problem(Code.MISSING_FILE, f"{target} does not exist") for target in missing]


def check_embedded(references: list[str], images: list[str]) -> list[Problem]:
    stray = sorted(set(references) - set(images))
    return [Problem(Code.MISSING_FILE, f"{target} is referenced but not embedded") for target in stray]


def check_unreferenced(images: list[str], references: list[str]) -> list[Problem]:
    silent = sorted(set(images) - set(references))
    return [Problem(Code.UNREFERENCED_FIGURE, f"{target} is never referenced in the text") for target in silent]


def check_orphans(images: list[str], directory: Path) -> list[Problem]:
    figures = directory / FIGURE_DIRECTORY
    on_disk = {f"{FIGURE_DIRECTORY}/{path.name}" for path in figures.glob("*.png")}
    orphans = sorted(on_disk - set(images))
    return [Problem(Code.UNREFERENCED_FIGURE, f"{target} is on disk but not in the report") for target in orphans]


def check_main(sections: Sections) -> list[Problem]:
    if references_in(sections.main):
        return []
    return [Problem(Code.MAIN_WITHOUT_FIGURE, "the main section references no figure")]


def check_lines(lines: list[str], directory: Path) -> list[Problem]:
    sections = split_sections(without_fences(lines))
    images = images_in(sections.opening) + images_in(sections.body)
    references = references_in(sections.body)
    return [
        *check_opening(sections),
        *check_order(sections),
        *check_numbering(images),
        *check_files([*images, *references], directory),
        *check_embedded(references, images),
        *check_unreferenced(images, references),
        *check_orphans(images, directory),
        *check_main(sections),
    ]


def check(directory: Path) -> list[Problem]:
    report = directory / REPORT_NAME
    if not report.is_file():
        return [Problem(Code.MISSING_REPORT, f"{report} does not exist")]
    return check_lines(report.read_text().splitlines(), directory)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Check the structure of a preview report")
    result.add_argument("directory", type=Path)
    return result


def main() -> int:
    problems = check(parser().parse_args().directory)
    for problem in problems:
        print(problem, file=sys.stderr)
    if not problems:
        print("ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
