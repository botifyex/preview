import json
import re
from pathlib import Path
from typing import Any

import pytest
from helpers import SAVE, Capture, box, figure


@pytest.mark.parametrize(
    "anchor",
    [{"selector": "#missing"}, {"role": "button", "name": "Nope"}, {"text": "Nope"}, {"selector": "#hidden"}],
)
def test_anchor_miss_fails_and_names_the_anchor(capture: Capture, anchor: dict[str, Any]) -> None:
    message = capture.failure(figure({"kind": "box", "anchor": anchor}))
    assert "matched no visible element" in message
    assert next(iter(anchor.values())) in message


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


def test_documented_spec_example_is_valid(capture: Capture, monkeypatch: pytest.MonkeyPatch) -> None:
    reference = Path(__file__).parent.parent.parent / "skills/preview/references/capture-spec.md"
    block = re.search(r"## Spec\n\n```json\n(.*?)```", reference.read_text(), re.DOTALL)
    assert block
    example = json.loads(block[1])
    example["base_url"] = capture.site
    monkeypatch.setenv("PREVIEW_PASSWORD", "throwaway-secret")
    process = capture.run(example)
    assert process.returncode == 0, process.stderr
    manifest = json.loads((capture.out / "figures" / "manifest.json").read_text())
    assert [entry["file"] for entry in manifest["figures"]] == ["figures/01-export-button.png"]
    assert manifest["figures"][0]["marks"][0]["text"] == "New button"
    assert (capture.out / "figures" / "01-export-button.png").is_file()


def test_self_signed_certificate_needs_the_flag(tmp_path: Path, secure_site: str) -> None:
    capture = Capture(tmp_path, secure_site)
    process = capture.run({"figures": [figure(box("#save"))]})
    assert process.returncode == 1
    assert "ERR_CERT" in process.stderr
    process = capture.run({"figures": [figure(box("#save"))]}, "--ignore-https-errors")
    assert process.returncode == 0, process.stderr


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
