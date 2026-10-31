import itertools
from dataclasses import asdict, dataclass

from capture.model import Box, CaptureFailure, Spec
from capture.scheme.constants import SEQUENCE
from capture.scheme.layout import Sheet
from capture.scheme.placement import label_box
from capture.scheme.routing import Point, Request, Route, routed


@dataclass(frozen=True)
class Drawn:
    link: Spec
    route: Route
    label: Box | None


def links_of(figure: Spec, identities: list[str | int]) -> list[Spec]:
    links = figure.get("links", [])
    if links != SEQUENCE:
        return links
    return [{"from": first, "to": second} for first, second in itertools.pairwise(identities)]


def position(identities: list[str | int], identity: str | int) -> int:
    return [str(item) for item in identities].index(str(identity))


def mark_point(link: Spec, source: Spec, where: str) -> Point | None:
    if "from_mark" not in link:
        return None
    number = link["from_mark"]
    for mark in source["marks"]:
        if mark["number"] == number and mark["badge"]:
            return (mark["badge"]["x"], mark["badge"]["y"])
    raise CaptureFailure(f"{where}: panel {link['from']} has no mark {number}")


def route_links(links: list[Spec], panels: list[Spec], sheet: Sheet, slug: str) -> list[Route]:
    identities = [panel["id"] for panel in panels]
    routes: list[Route] = []
    for number, link in enumerate(links, 1):
        where = f"figure {slug} link {number}"
        source, target = position(identities, link["from"]), position(identities, link["to"])
        start = mark_point(link, panels[source], where)
        route = routed(Request(sheet.places[source].frame, sheet.places[target].frame, start), sheet, routes)
        if route is None:
            raise CaptureFailure(f"{where}: cannot route {link['from']} to {link['to']} without crossing a panel")
        routes.append(route)
    return routes


def placed_label(route: Route, width: float, sheet: Sheet, routes: list[Route], taken: list[Box], where: str) -> Box:
    frames = [place.frame for place in sheet.places]
    box = label_box(route, width, [*frames, *taken], routes, sheet.size)
    if box is None:
        raise CaptureFailure(f"{where}: text does not fit beside the arrow, shorten it or raise gap")
    return box


def drawn_links(links: list[Spec], routes: list[Route], widths: list[float], sheet: Sheet, slug: str) -> list[Drawn]:
    taken: list[Box] = []
    result: list[Drawn] = []
    for number, (link, route, width) in enumerate(zip(links, routes, widths, strict=True), 1):
        label = None
        if link.get("text"):
            label = placed_label(route, width, sheet, routes, taken, f"figure {slug} link {number}")
            taken.append(label)
        result.append(Drawn(link, route, label))
    return result


def point_entry(point: Point) -> Spec:
    return {"x": point[0], "y": point[1]}


def link_entry(drawn: Drawn) -> Spec:
    link, route = drawn.link, drawn.route
    return {
        "from": link["from"],
        "to": link["to"],
        "style": link.get("style", "solid"),
        "text": link.get("text"),
        "from_mark": link.get("from_mark"),
        "tail": point_entry(route[0]),
        "tip": point_entry(route[-1]),
        "points": [point_entry(point) for point in route],
        "label": None if drawn.label is None else asdict(drawn.label),
    }
