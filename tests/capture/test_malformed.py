import json
from pathlib import Path
from typing import Any

import pytest
from helpers import Capture, box, figure
from internals import internal
from support import run_script

EXAMPLE = Path(__file__).parent.parent.parent / "examples" / "todo-ui-refresh" / "figures" / "spec.json"

SPEC_CASES: dict[str, tuple[dict[str, Any], str]] = {
    "environment-number": ({"environment": 5}, "environment"),
    "environment-list": ({"environment": ["prod"]}, "environment"),
    "base-url-number": ({"base_url": 5}, "base_url"),
    "base-url-broken": ({"base_url": "http://["}, "base_url"),
    "locale-number": ({"locale": 5}, "locale"),
    "locale-invalid": ({"locale": "!!"}, "locale"),
    "placement-list": ({"placement": []}, "placement"),
    "hide-string": ({"hide": "nav"}, "hide"),
    "figures-object": ({"figures": {"slug": "x"}}, "figures"),
    "figures-string": ({"figures": "x"}, "figures"),
    "figures-number": ({"figures": 5}, "figures"),
    "figure-number": ({"figures": [5]}, "figure 1"),
    "figure-list": ({"figures": [[]]}, "figure 1"),
    "figure-string": ({"figures": ["x"]}, "figure 1"),
    "login-false": ({"login": False}, "login"),
    "login-list": ({"login": []}, "login"),
    "login-name-number": ({"login": {"name": 5, "steps": [], "expect": {}}}, "name"),
    "login-name-list": ({"login": {"name": [], "steps": [], "expect": {}}}, "name"),
    "login-steps-object": ({"login": {"name": "a", "steps": {"a": 1}, "expect": {"text": "a"}}}, "steps"),
    "login-steps-string": ({"login": {"name": "a", "steps": "a", "expect": {"text": "a"}}}, "steps"),
    "login-step-number": ({"login": {"name": "a", "steps": [5], "expect": {"text": "a"}}}, "step 1"),
    "login-expect-number": (
        {"login": {"name": "a", "steps": [{"action": "wait", "milliseconds": 1}], "expect": 5}},
        "login expect",
    ),
    "login-value-env-number": (
        {
            "login": {
                "name": "a",
                "steps": [{"action": "fill", "target": {"selector": "a"}, "value_env": 5}],
                "expect": {"text": "a"},
            }
        },
        "value_env",
    ),
}

FIGURE_CASES: dict[str, tuple[dict[str, Any], str]] = {
    "slug-number": ({"slug": 5}, "slug"),
    "slug-list": ({"slug": []}, "slug"),
    "url-number": ({"url": 5}, "url"),
    "url-broken": ({"url": "http://["}, "url"),
    "before-url-number": ({"before_url": 5}, "before_url"),
    "before-url-broken": ({"before_url": "http://["}, "before_url"),
    "theme-list": ({"theme": []}, "theme"),
    "theme-object": ({"theme": {}}, "theme"),
    "placement-list": ({"placement": []}, "placement"),
    "full-page-string": ({"full_page": "yes"}, "full_page"),
    "full-page-number": ({"full_page": 1}, "full_page"),
    "viewport-number": ({"viewport": 5}, "viewport"),
    "viewport-list": ({"viewport": []}, "viewport"),
    "width-string": ({"viewport": {"width": "x"}}, "width"),
    "width-zero": ({"viewport": {"width": 0}}, "width"),
    "width-true": ({"viewport": {"width": True}}, "width"),
    "width-fraction": ({"viewport": {"width": 10.5}}, "width"),
    "width-huge": ({"viewport": {"width": 10**400}}, "width"),
    "height-negative": ({"viewport": {"height": -1}}, "height"),
    "scale-string": ({"viewport": {"scale": "x"}}, "scale"),
    "scale-zero": ({"viewport": {"scale": 0}}, "scale"),
    "scale-nan": ({"viewport": {"scale": float("nan")}}, "scale"),
    "steps-object": ({"steps": {"a": 1}}, "steps"),
    "steps-string": ({"steps": "x"}, "steps"),
    "step-number": ({"steps": [5]}, "step 1"),
    "annotations-number": ({"annotations": 5}, "annotations"),
    "annotations-object": ({"annotations": {"a": 1}}, "annotations"),
    "annotation-string": ({"annotations": ["x"]}, "annotation 1"),
    "before-steps-string": ({"before_steps": "x"}, "before_steps"),
    "before-annotations-number": ({"before_annotations": 5}, "before_annotations"),
}

STEP_CASES: dict[str, tuple[dict[str, Any], str]] = {
    "action-list": ({"action": []}, "action"),
    "action-object": ({"action": {}}, "action"),
    "action-number": ({"action": 5}, "action"),
    "url-number": ({"action": "goto", "url": 5}, "url"),
    "url-broken": ({"action": "goto", "url": "http://["}, "url"),
    "value-number": ({"action": "fill", "target": {"selector": "a"}, "value": 5}, "value"),
    "value-null": ({"action": "fill", "target": {"selector": "a"}, "value": None}, "value"),
    "value-env-number": ({"action": "fill", "target": {"selector": "a"}, "value_env": 5}, "value_env"),
    "key-number": ({"action": "press", "key": 5}, "key"),
    "milliseconds-string": ({"action": "wait", "milliseconds": "x"}, "milliseconds"),
    "milliseconds-true": ({"action": "wait", "milliseconds": True}, "milliseconds"),
    "milliseconds-negative": ({"action": "wait", "milliseconds": -1}, "milliseconds"),
    "milliseconds-nan": ({"action": "wait", "milliseconds": float("nan")}, "milliseconds"),
    "milliseconds-list": ({"action": "wait", "milliseconds": []}, "milliseconds"),
    "target-number": ({"action": "click", "target": 5}, "target"),
    "target-list": ({"action": "click", "target": []}, "target"),
}

ANCHOR = {"selector": "#save"}

ANNOTATION_CASES: dict[str, tuple[dict[str, Any], str]] = {
    "kind-list": ({"kind": [], "anchor": ANCHOR}, "kind"),
    "kind-object": ({"kind": {}, "anchor": ANCHOR}, "kind"),
    "kind-number": ({"kind": 5, "anchor": ANCHOR}, "kind"),
    "anchor-number": ({"kind": "box", "anchor": 5}, "target"),
    "from-number": ({"kind": "arrow", "anchor": ANCHOR, "from": 5}, "target"),
    "placement-list": ({"kind": "box", "anchor": ANCHOR, "placement": []}, "placement"),
    "placement-object": ({"kind": "box", "anchor": ANCHOR, "placement": {}}, "placement"),
    "number-string": ({"kind": "box", "anchor": ANCHOR, "number": "1"}, "number"),
    "number-true": ({"kind": "box", "anchor": ANCHOR, "number": True}, "number"),
    "number-fraction": ({"kind": "box", "anchor": ANCHOR, "number": 1.5}, "number"),
    "number-list": ({"kind": "badge", "anchor": ANCHOR, "number": []}, "number"),
    "text-number": ({"kind": "label", "anchor": ANCHOR, "text": 5}, "text"),
    "text-null": ({"kind": "label", "anchor": ANCHOR, "text": None}, "text"),
    "offset-number": ({"kind": "arrow", "anchor": ANCHOR, "offset": 5}, "offset"),
    "offset-list": ({"kind": "removed", "anchor": ANCHOR, "offset": []}, "offset"),
    "offset-x-string": ({"kind": "arrow", "anchor": ANCHOR, "offset": {"x": "a"}}, "offset"),
    "offset-y-true": ({"kind": "arrow", "anchor": ANCHOR, "offset": {"y": True}}, "offset"),
    "offset-x-nan": ({"kind": "arrow", "anchor": ANCHOR, "offset": {"x": float("nan")}}, "offset"),
    "offset-x-infinity": ({"kind": "arrow", "anchor": ANCHOR, "offset": {"x": float("inf")}}, "offset"),
    "offset-x-huge": ({"kind": "arrow", "anchor": ANCHOR, "offset": {"x": 10**400}}, "offset"),
    "offset-width-string": ({"kind": "removed", "anchor": ANCHOR, "offset": {"width": "a"}}, "offset"),
    "offset-height-zero": ({"kind": "removed", "anchor": ANCHOR, "offset": {"height": 0}}, "offset"),
}

LOCATOR_CASES: dict[str, tuple[dict[str, Any], str]] = {
    "selector-number": ({"selector": 5}, "selector"),
    "selector-list": ({"selector": []}, "selector"),
    "role-number": ({"role": 5}, "role"),
    "text-number": ({"text": 5}, "text"),
    "text-null": ({"text": None}, "text"),
    "text-list": ({"text": []}, "text"),
    "name-number": ({"role": "button", "name": 5}, "name"),
    "name-null": ({"role": "button", "name": None}, "name"),
    "name-list": ({"role": "button", "name": []}, "name"),
    "match-list": ({"text": "a", "match": []}, "match"),
    "match-object": ({"text": "a", "match": {}}, "match"),
    "regex-text-number": ({"text": 5, "match": "regex"}, "text"),
    "regex-name-number": ({"role": "button", "name": 5, "match": "regex"}, "name"),
    "regex-too-large": ({"text": "a{99999999999}", "match": "regex"}, "regex"),
}


def refused(process: Any, fragment: str) -> None:
    assert process.returncode == 1, process.stdout
    assert process.stderr.startswith("error: "), process.stderr
    assert "Traceback" not in process.stderr
    assert fragment in process.stderr, process.stderr


@pytest.mark.parametrize(("change", "fragment"), SPEC_CASES.values(), ids=SPEC_CASES.keys())
def test_malformed_spec_field(capture: Capture, change: dict[str, Any], fragment: str) -> None:
    refused(capture.run({"figures": [figure()], **change}), fragment)


@pytest.mark.parametrize(("change", "fragment"), FIGURE_CASES.values(), ids=FIGURE_CASES.keys())
def test_malformed_figure_field(capture: Capture, change: dict[str, Any], fragment: str) -> None:
    refused(capture.run({"figures": [{**figure(), **change}]}), fragment)


@pytest.mark.parametrize(("step", "fragment"), STEP_CASES.values(), ids=STEP_CASES.keys())
def test_malformed_step(capture: Capture, step: dict[str, Any], fragment: str) -> None:
    refused(capture.run({"figures": [figure(steps=[step])]}), fragment)


@pytest.mark.parametrize(("annotation", "fragment"), ANNOTATION_CASES.values(), ids=ANNOTATION_CASES.keys())
def test_malformed_annotation(capture: Capture, annotation: dict[str, Any], fragment: str) -> None:
    refused(capture.run({"figures": [figure(annotation)]}), fragment)


@pytest.mark.parametrize(("anchor", "fragment"), LOCATOR_CASES.values(), ids=LOCATOR_CASES.keys())
def test_malformed_locator(capture: Capture, anchor: dict[str, Any], fragment: str) -> None:
    refused(capture.run({"figures": [figure({"kind": "box", "anchor": anchor})]}), fragment)


@pytest.mark.parametrize(
    "content",
    [b"[]", b'"text"', b"5", b"null", b"true", b"\xff\xfe\x00", b"[" * 200000, b"{broken"],
    ids=["list", "string", "number", "null", "true", "not-utf8", "too-deep", "broken"],
)
def test_malformed_spec_file(tmp_path: Path, content: bytes) -> None:
    path = tmp_path / "spec.json"
    path.write_bytes(content)
    refused(run_script("run_capture.py", str(path), "--out", str(tmp_path / "out")), "spec")


@pytest.mark.parametrize("value", [True, 0, 1, "false", None, [], {}], ids=repr)
def test_figure_login_may_only_be_false(capture: Capture, value: Any) -> None:
    refused(capture.run({"figures": [figure(login=value)]}), "login may only be false")


@pytest.mark.parametrize(
    "anchor",
    [{"text": None}, {"role": "button", "name": 5}, {"role": "button", "name": None}, {"role": "button", "name": []}],
    ids=repr,
)
def test_locator_text_and_name_are_refused_before_any_browser_work(capture: Capture, anchor: dict[str, Any]) -> None:
    refused(capture.run({"figures": [figure({"kind": "box", "anchor": anchor})]}), "must be a string")
    assert not capture.out.exists()


def test_figure_login_false_passes(capture: Capture) -> None:
    capture.figures(figure(login=False))


def test_non_ascii_spec_is_read_as_utf8_in_any_locale(capture: Capture, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LC_ALL", "C")
    monkeypatch.setenv("PYTHONUTF8", "0")
    monkeypatch.setenv("PYTHONCOERCECLOCALE", "0")
    capture.figures(figure(box("#save", text="Сохранить")))
    saved = json.loads((capture.out / "figures" / "spec.json").read_text(encoding="utf-8"))
    assert saved["figures"][0]["annotations"][0]["text"] == "Сохранить"


def test_example_spec_passes_validation() -> None:
    internal("validation").validate_spec(json.loads(EXAMPLE.read_text(encoding="utf-8")))
