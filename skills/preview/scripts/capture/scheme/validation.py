from typing import Any

from capture.colors import is_color
from capture.fields import demand_list, demand_object, demand_string, demand_url, is_choice, is_integer
from capture.figure_fields import is_slug, validate_figure_options
from capture.items import validate_annotations, validate_locator, validate_steps
from capture.model import CaptureFailure, Spec, demand
from capture.scheme.constants import (
    CONTEXT_FIELDS,
    FIGURE_ONLY_FIELDS,
    LAYOUTS,
    LINK_STYLES,
    PANEL_ONLY_FIELDS,
    SEQUENCE,
    SIDE_LIMIT,
)


def panel_identity(panel: Spec, index: int) -> str | int:
    return panel.get("id", index)


def is_side(value: Any) -> bool:
    return is_integer(value) and 0 < value <= SIDE_LIMIT


def is_size(value: Any) -> bool:
    return is_integer(value) and 0 <= value <= SIDE_LIMIT


def validate_crop(panel: Spec, where: str) -> None:
    if "crop" in panel:
        validate_locator(panel["crop"], f"{where} crop")
    if "crop_padding" in panel:
        demand("crop" in panel, f"{where}: crop_padding requires crop")
        demand(is_size(panel["crop_padding"]), f"{where}: crop_padding must be an integer from 0 to {SIDE_LIMIT}")


def validate_context_fields(panel: Spec, where: str) -> None:
    for field in CONTEXT_FIELDS:
        demand(field not in panel, f"{where}: {field} does not apply with continuous")


def validate_panel(panel: Any, where: str, continuous: bool, first: bool) -> None:
    demand_object(panel, f"{where}: must be an object")
    demand("url" in panel or (continuous and not first), f"{where}: url is required")
    if continuous:
        validate_context_fields(panel, where)
    demand_url(panel, "url", where)
    for field in PANEL_ONLY_FIELDS:
        demand(field not in panel, f"{where}: {field} does not apply to a panel")
    validate_figure_options(panel, where)
    validate_steps(panel, "steps", where, where)
    validate_annotations(panel, "annotations", where, where)
    demand_string(panel, "title", where)
    if "id" in panel:
        demand(is_slug(panel["id"]), f"{where}: id must be lowercase words joined by hyphens")
    validate_crop(panel, where)


def validate_panels(figure: Spec, where: str) -> None:
    panels = demand_list(figure, "panels", where)
    demand(panels, f"{where}: panels must not be empty")
    continuous = figure.get("continuous", False)
    identities: set[str] = set()
    for index, panel in enumerate(panels, 1):
        validate_panel(panel, f"{where} panel {index}", continuous, index == 1)
        identity = str(panel_identity(panel, index))
        demand(identity not in identities, f"{where}: duplicate panel id {identity}")
        identities.add(identity)


def validate_arrangement(figure: Spec, where: str) -> None:
    layout = figure.get("layout", "row")
    demand(is_choice(layout, LAYOUTS), f"{where}: layout must be row, column or grid")
    if layout == "grid":
        demand("columns" in figure, f"{where}: grid requires columns")
    if "columns" in figure:
        demand(layout == "grid", f"{where}: columns applies to a grid only")
        demand(is_side(figure["columns"]), f"{where}: columns must be a positive integer up to {SIDE_LIMIT}")
    if "panel_width" in figure:
        demand(is_side(figure["panel_width"]), f"{where}: panel_width must be a positive integer up to {SIDE_LIMIT}")
    if "gap" in figure:
        demand(is_size(figure["gap"]), f"{where}: gap must be an integer from 0 to {SIDE_LIMIT}")
    if "background" in figure:
        demand(is_color(figure["background"]), f"{where}: background must be #RRGGBB")
    demand(isinstance(figure.get("steps_numbers", False), bool), f"{where}: steps_numbers must be true or false")


def find_panel(figure: Spec, identity: Any, where: str) -> Spec:
    valid = (is_integer(identity) or isinstance(identity, str)) and identity != ""
    demand(valid, f"{where}: from and to must be a panel id")
    for index, panel in enumerate(figure["panels"], 1):
        if str(panel_identity(panel, index)) == str(identity):
            return panel
    raise CaptureFailure(f"{where}: unknown panel {identity}")


def validate_mark(link: Spec, source: Spec, where: str) -> None:
    number = link["from_mark"]
    demand(is_integer(number), f"{where}: from_mark must be an integer")
    numbers = [annotation.get("number") for annotation in source.get("annotations", [])]
    demand(number in numbers, f"{where}: panel {link['from']} has no mark {number}")
    demand(numbers.count(number) == 1, f"{where}: panel {link['from']} has mark {number} twice")


def validate_link(link: Any, figure: Spec, where: str) -> None:
    demand_object(link, f"{where}: must be an object")
    for field in ("from", "to"):
        demand(field in link, f"{where}: {field} is required")
    source = find_panel(figure, link["from"], where)
    target = find_panel(figure, link["to"], where)
    demand(source is not target, f"{where}: a link must join two panels")
    demand_string(link, "text", where)
    demand(is_choice(link.get("style", "solid"), LINK_STYLES), f"{where}: style must be solid or dashed")
    if "from_mark" in link:
        validate_mark(link, source, where)


def validate_links(figure: Spec, where: str) -> None:
    links = figure.get("links", [])
    if links == SEQUENCE:
        demand(figure.get("layout", "row") != "grid", f"{where}: links sequence applies to a row or a column")
        return
    demand(isinstance(links, list), f"{where}: links must be a list or sequence")
    for index, link in enumerate(links, 1):
        validate_link(link, figure, f"{where} link {index}")


def validate_scheme(figure: Spec, where: str) -> None:
    for field in FIGURE_ONLY_FIELDS:
        demand(field not in figure, f"{where}: {field} does not apply with panels")
    validate_figure_options(figure, where)
    demand(isinstance(figure.get("continuous", False), bool), f"{where}: continuous must be true or false")
    validate_panels(figure, where)
    validate_arrangement(figure, where)
    validate_links(figure, where)
