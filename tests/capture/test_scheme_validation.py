from typing import Any

import pytest
from helpers import Capture
from internals import internal
from scheme_helpers import panel, scheme

validation = internal("validation")
model = internal("model")


def marked(number: int) -> dict[str, Any]:
    return panel(annotations=[{"kind": "box", "anchor": {"selector": "#card"}, "number": number}])


def twice(number: int) -> dict[str, Any]:
    box = {"kind": "box", "anchor": {"selector": "#card"}, "number": number}
    return panel(annotations=[box, box])


TWO = (panel(), panel())
CASES: list[tuple[dict[str, Any], str]] = [
    ({"slug": "s", "panels": 3}, "panels must be a list"),
    ({"slug": "s", "panels": []}, "panels must not be empty"),
    ({"slug": "s", "panels": [panel()], "url": "a"}, "url does not apply with panels"),
    ({"slug": "s", "panels": [panel()], "before_url": "a"}, "before_url does not apply with panels"),
    ({"slug": "s", "panels": [panel()], "steps": []}, "steps does not apply with panels"),
    ({"slug": "s", "panels": [panel()], "annotations": []}, "annotations does not apply with panels"),
    ({"slug": "s", "panels": [panel()], "full_page": True}, "full_page does not apply with panels"),
    ({"slug": "s", "panels": [panel()], "theme": "sepia"}, "theme must be light or dark"),
    ({"slug": "s", "panels": [7]}, "panel 1: must be an object"),
    ({"slug": "s", "panels": [{}]}, "panel 1: url is required"),
    (scheme(panel(), {"url": 5}), "panel 2: url must be a valid address"),
    (scheme(panel(title=5)), "panel 1: title must be a string"),
    (scheme(panel(id="Not Slug")), "panel 1: id must be lowercase"),
    (scheme(panel(id=5)), "panel 1: id must be lowercase"),
    (scheme(panel(id="a"), panel(id="a")), "duplicate panel id a"),
    (scheme(panel(id="2"), panel()), "duplicate panel id 2"),
    (scheme(panel(crop=5)), "panel 1 crop: target must be an object"),
    (scheme(panel(crop={"selector": "#a"}, crop_padding=-1)), "crop_padding must be an integer"),
    (scheme(panel(crop={"selector": "#a"}, crop_padding="4")), "crop_padding must be an integer"),
    (scheme(panel(crop_padding=4)), "crop_padding requires crop"),
    (scheme(panel(full_page="yes")), "panel 1: full_page must be true or false"),
    (scheme(panel(login=True)), "panel 1: login may only be false"),
    (scheme(panel(viewport={"width": 0})), "panel 1: viewport width"),
    (scheme(panel(theme="sepia")), "panel 1: theme must be"),
    (scheme(panel(placement="nowhere")), "panel 1: placement must be"),
    (scheme(panel(color="red")), "panel 1: color must be"),
    (scheme(panel(steps=[{"action": "dance"}])), "panel 1 step 1: unknown action"),
    (scheme(panel(annotations=[{"kind": "wave"}])), "panel 1 annotation 1: unknown annotation kind"),
    (scheme(panel(before_url="a")), "panel 1: before_url does not apply"),
    (scheme(panel(panels=[])), "panel 1: panels does not apply"),
    (scheme(panel(), layout="circle"), "layout must be row, column or grid"),
    (scheme(panel(), layout=3), "layout must be row, column or grid"),
    (scheme(panel(), layout="grid"), "grid requires columns"),
    (scheme(panel(), columns=2), "columns applies to a grid only"),
    (scheme(panel(), layout="row", columns=2), "columns applies to a grid only"),
    (scheme(panel(), layout="grid", columns=0), "columns must be a positive integer"),
    (scheme(panel(), layout="grid", columns="2"), "columns must be a positive integer"),
    (scheme(panel(), panel_width=0), "panel_width must be a positive integer"),
    (scheme(panel(), panel_width=1.5), "panel_width must be a positive integer"),
    (scheme(panel(), panel_width=9000), "panel_width must be a positive integer"),
    (scheme(panel(), gap=-1), "gap must be an integer"),
    (scheme(panel(), gap="8"), "gap must be an integer"),
    (scheme(panel(), background="white"), "background must be #RRGGBB"),
    (scheme(panel(), steps_numbers=1), "steps_numbers must be true or false"),
    (scheme(*TWO, links="next"), "links must be a list or sequence"),
    (scheme(*TWO, links={"from": 1}), "links must be a list or sequence"),
    (scheme(*TWO, layout="grid", columns=2, links="sequence"), "links sequence applies to a row or a column"),
    (scheme(*TWO, links=[5]), "link 1: must be an object"),
    (scheme(*TWO, links=[{"to": 1}]), "link 1: from is required"),
    (scheme(*TWO, links=[{"from": 1}]), "link 1: to is required"),
    (scheme(*TWO, links=[{"from": 1, "to": 9}]), "link 1: unknown panel 9"),
    (scheme(*TWO, links=[{"from": "ghost", "to": 2}]), "link 1: unknown panel ghost"),
    (scheme(*TWO, links=[{"from": True, "to": 2}]), "link 1: from and to must be a panel id"),
    (scheme(*TWO, links=[{"from": 1, "to": 1}]), "link 1: a link must join two panels"),
    (scheme(*TWO, links=[{"from": 1, "to": 2, "text": 5}]), "link 1: text must be a string"),
    (scheme(*TWO, links=[{"from": 1, "to": 2, "style": "wavy"}]), "link 1: style must be solid or dashed"),
    (scheme(*TWO, links=[{"from": 1, "to": 2, "from_mark": "1"}]), "link 1: from_mark must be an integer"),
    (scheme(*TWO, links=[{"from": 1, "to": 2, "from_mark": 3}]), "link 1: panel 1 has no mark 3"),
    (scheme(marked(1), panel(), links=[{"from": 1, "to": 2, "from_mark": 2}]), "link 1: panel 1 has no mark 2"),
    (scheme(twice(1), panel(), links=[{"from": 1, "to": 2, "from_mark": 1}]), "link 1: panel 1 has mark 1 twice"),
]


@pytest.mark.parametrize(("figure", "message"), CASES, ids=[message for _, message in CASES])
def test_a_bad_scheme_is_refused(figure: dict[str, Any], message: str) -> None:
    spec = {"environment": "test", "base_url": "http://localhost/", "figures": [figure]}
    with pytest.raises(model.CaptureFailure, match=message):
        validation.validate_spec(spec)


def test_refusal_reaches_the_command_line_before_the_browser(capture: Capture) -> None:
    capture.site = "http://127.0.0.1:9/"
    stderr = capture.failure(scheme(panel(), layout="circle"))
    assert stderr.startswith("error: figure 1 (scheme): layout must be row, column or grid")
    assert not capture.out.exists()


def test_repeated_numbers_no_link_names_stay_allowed() -> None:
    linked = [{"from": 2, "to": 1, "from_mark": 1}]
    spec = {
        "environment": "test",
        "base_url": "http://localhost/",
        "figures": [scheme(twice(1), marked(1), links=linked), scheme(twice(1), slug="other")],
    }
    validation.validate_spec(spec)
