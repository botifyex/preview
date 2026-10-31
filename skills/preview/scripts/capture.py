#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["playwright==1.64.1"]
# ///
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from playwright.sync_api import Browser, BrowserContext, Error as PlaywrightError
from playwright.sync_api import Locator, Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeout


class CaptureFailure(Exception):
    pass


type Spec = dict[str, Any]

PLAYWRIGHT_VERSION = "1.64.1"
PRODUCTION_NAMES = frozenset({"production", "prod", "live"})
THEMES = frozenset({"light", "dark"})
DEFAULT_VIEWPORT = {"width": 1280, "height": 800, "scale": 1}
SLUG_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
FIGURE_PATTERN = re.compile(r"\d{2,}-.+\.png")
MANIFEST_NAME = "manifest.json"
SPEC_NAME = "spec.json"
FAILURES_NAME = "failures"
IDENTITY_LENGTH = 12
BADGE_MARGIN = 16
BADGE_REACH = 20
BADGE_INSET = 18
TAIL_PLACEMENTS = frozenset({"corner", "top-left"})
OUTSIDE_PLACEMENTS = frozenset({"left", "right", "above", "below"})
ARROW_PLACEMENTS = TAIL_PLACEMENTS | OUTSIDE_PLACEMENTS
PLACEMENTS = ARROW_PLACEMENTS | frozenset({"top-right", "bottom-left", "bottom-right", "inside"})
DEFAULT_PLACEMENT = "corner"
MATCH_KINDS = frozenset({"exact", "substring", "regex"})
FLAG_FIELDS = ("has_touch", "reduced_motion")
BOX_PADDING = 4
EDGE_MARGIN = 2
ARROW_REACH = (80, 60)
MARK_ADVICE = 5
IDLE_LIMIT = 3000
STABLE_POLL = 100
STEP_FIELDS: dict[str, frozenset[str]] = {
    "goto": frozenset({"url"}),
    "fill": frozenset({"target"}),
    "click": frozenset({"target"}),
    "hover": frozenset({"target"}),
    "press": frozenset({"key"}),
    "wait": frozenset(),
}
ANNOTATION_FIELDS: dict[str, frozenset[str]] = {
    "box": frozenset({"anchor"}),
    "arrow": frozenset({"anchor"}),
    "badge": frozenset({"anchor", "number"}),
    "label": frozenset({"anchor", "text"}),
    "removed": frozenset({"anchor", "offset"}),
}
LOCATOR_KEYS = frozenset({"selector", "role", "text"})

SETTLE_SCRIPT = """
async (limit) => {
  await document.fonts.ready;
  const endless = (animation) => animation.effect?.getComputedTiming().iterations === Infinity;
  const animations = document.getAnimations();
  animations.filter(endless).forEach((animation) => animation.cancel());
  const running = animations.filter((animation) => !endless(animation) && animation.playState === "running");
  const finished = Promise.allSettled(running.map((animation) => animation.finished)).then(() => true);
  const expired = new Promise((resolve) => setTimeout(() => resolve(false), limit));
  const settled = await Promise.race([finished, expired]);
  await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  return settled;
}
"""

MEASURE_SCRIPT = """
(element) => {
  const rectangle = element.getBoundingClientRect();
  let left = rectangle.left, top = rectangle.top, right = rectangle.right, bottom = rectangle.bottom;
  for (let parent = element.parentElement; parent && parent !== document.body; parent = parent.parentElement) {
    if (getComputedStyle(parent).overflow === "visible") continue;
    const outer = parent.getBoundingClientRect();
    left = Math.max(left, outer.left);
    top = Math.max(top, outer.top);
    right = Math.min(right, outer.right);
    bottom = Math.min(bottom, outer.bottom);
  }
  if (right <= left || bottom <= top) return null;
  return { x: left + scrollX, y: top + scrollY, width: right - left, height: bottom - top };
}
"""

PAGE_SCRIPT = """
() => ({
  width: Math.max(document.documentElement.scrollWidth, document.body?.scrollWidth ?? 0),
  height: Math.max(document.documentElement.scrollHeight, document.body?.scrollHeight ?? 0),
  left: scrollX,
  top: scrollY,
  viewportWidth: innerWidth,
  viewportHeight: innerHeight,
})
"""

HIDE_SCRIPT = "(elements) => elements.forEach((element) => element.style.setProperty('display', 'none', 'important'))"

SCROLL_TOP_SCRIPT = "() => window.scrollTo({ top: 0, left: 0, behavior: 'instant' })"

DRAW_SCRIPT = """
({ marks, page }) => {
  const ACCENT = "#E6007E", REMOVED = "#C81E1E", HALO = "#FFFFFF", INK = "#FFFFFF";
  const NAMESPACE = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(NAMESPACE, "svg");
  svg.setAttribute("data-preview", "overlay");
  svg.setAttribute("width", page.width);
  svg.setAttribute("height", page.height);
  Object.assign(svg.style, {
    position: "absolute", left: "0", top: "0", width: page.width + "px", height: page.height + "px",
    zIndex: "2147483647", pointerEvents: "none", overflow: "visible", margin: "0", maxWidth: "none",
  });
  document.documentElement.appendChild(svg);
  const origin = svg.getBoundingClientRect();
  svg.style.left = -(origin.left + scrollX) + "px";
  svg.style.top = -(origin.top + scrollY) + "px";
  const add = (name, attributes, text) => {
    const node = document.createElementNS(NAMESPACE, name);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
    if (text !== undefined) node.textContent = text;
    svg.appendChild(node);
    return node;
  };
  const outlined = (name, attributes, color, dash) => {
    add(name, { ...attributes, fill: "none", stroke: HALO, "stroke-width": 7, "stroke-opacity": 0.9, "stroke-linecap": "round" });
    add(name, { ...attributes, fill: "none", stroke: color, "stroke-width": 3, "stroke-linecap": "round", ...(dash ? { "stroke-dasharray": dash } : {}) });
  };
  const frame = (mark, color, dash) => outlined("rect", { x: mark.rectangle.x, y: mark.rectangle.y, width: mark.rectangle.width, height: mark.rectangle.height, rx: 4 }, color, dash);
  const arrow = (mark) => {
    const { tail, tip } = mark;
    const angle = Math.atan2(tip.y - tail.y, tip.x - tail.x);
    const wing = (turn) => (tip.x - 14 * Math.cos(angle + turn)) + "," + (tip.y - 14 * Math.sin(angle + turn));
    const points = tip.x + "," + tip.y + " " + wing(0.5) + " " + wing(-0.5);
    outlined("line", { x1: tail.x, y1: tail.y, x2: tip.x, y2: tip.y }, ACCENT);
    add("polygon", { points, fill: ACCENT, stroke: HALO, "stroke-width": 2 });
  };
  const badge = (mark, color) => {
    const { x, y } = mark.badge;
    add("circle", { cx: x, cy: y, r: 14, fill: color, stroke: HALO, "stroke-width": 3 });
    add("text", { x, y, fill: INK, "font-family": "Arial, sans-serif", "font-size": 15, "font-weight": 700, "text-anchor": "middle", "dominant-baseline": "central" }, String(mark.number));
  };
  const label = (mark, color) => {
    const text = add("text", { x: 0, y: 0, fill: INK, "font-family": "Arial, sans-serif", "font-size": 14, "font-weight": 700, "dominant-baseline": "central" }, mark.text);
    const width = text.getBBox().width + 16, height = 24;
    if (width > page.width) throw new Error("label is wider than the page: " + mark.text);
    const above = mark.corner.y - height - 8;
    const y = above >= 0 ? above : mark.bottom + 8;
    const start = mark.corner.x + (mark.number === null ? 0 : 20);
    const x = Math.max(0, Math.min(page.width - width, start));
    const back = add("rect", { x, y, width, height, rx: 4, fill: color, stroke: HALO, "stroke-width": 2 });
    svg.insertBefore(back, text);
    text.setAttribute("x", x + 8);
    text.setAttribute("y", y + height / 2);
  };
  for (const mark of marks) {
    const color = mark.kind === "removed" ? REMOVED : ACCENT;
    if (mark.kind === "box") frame(mark, color);
    if (mark.kind === "removed") frame(mark, color, "10 7");
    if (mark.kind === "arrow") arrow(mark);
    if (mark.text !== null) label(mark, color);
    if (mark.number !== null) badge(mark, color);
  }
}
"""


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    width: float
    height: float

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    def inside(self, left: float, top: float, right: float, bottom: float) -> bool:
        return self.x >= left and self.y >= top and self.right <= right and self.bottom <= bottom


@dataclass(frozen=True)
class Options:
    output: Path
    state_directory: Path
    ignore_https: bool
    fresh_login: bool
    timeout: int


@dataclass(frozen=True)
class Shot:
    slug: str
    url: str
    steps: list[Spec]
    annotations: list[Spec]
    figure: Spec
    role: str


def demand(condition: Any, message: str) -> None:
    if not condition:
        raise CaptureFailure(message)


def describe_locator(target: Spec) -> str:
    return json.dumps({key: target[key] for key in sorted(target) if key in LOCATOR_KEYS | {"name", "match"}}, ensure_ascii=False)


def validate_match(target: Spec, where: str) -> None:
    kind = target.get("match", "exact")
    demand(kind in MATCH_KINDS, f"{where}: match must be exact, substring or regex")
    if "match" not in target:
        return
    pattern = target.get("text", target.get("name"))
    demand(pattern is not None, f"{where}: match applies to text or a role name")
    if kind == "regex":
        try:
            re.compile(pattern)
        except re.error as failure:
            raise CaptureFailure(f"{where}: match regex is invalid: {failure}") from failure


def validate_locator(target: Any, where: str) -> None:
    demand(isinstance(target, dict), f"{where}: target must be an object")
    keys = LOCATOR_KEYS & set(target)
    demand(len(keys) == 1, f"{where}: exactly one of selector, role, text is required")
    validate_match(target, where)


def validate_step(step: Spec, where: str) -> None:
    kind = step.get("action")
    demand(kind in STEP_FIELDS, f"{where}: unknown action {kind!r}")
    missing = STEP_FIELDS[kind] - set(step)
    demand(not missing, f"{where}: {kind} requires {sorted(missing)}")
    if "target" in step:
        validate_locator(step["target"], where)
    if kind == "fill":
        demand(("value" in step) != ("value_env" in step), f"{where}: fill requires value or value_env")
    if kind == "wait":
        demand(("target" in step) != ("milliseconds" in step), f"{where}: wait requires target or milliseconds")


def validate_steps(steps: list[Spec], where: str) -> None:
    for index, step in enumerate(steps, 1):
        validate_step(step, f"{where} step {index}")


def validate_placement(placement: Any, where: str) -> None:
    demand(placement in PLACEMENTS, f"{where}: placement must be one of {sorted(PLACEMENTS)}")


def validate_annotation(annotation: Spec, where: str) -> None:
    kind = annotation.get("kind")
    demand(kind in ANNOTATION_FIELDS, f"{where}: unknown annotation kind {kind!r}")
    missing = ANNOTATION_FIELDS[kind] - set(annotation)
    demand(not missing, f"{where}: {kind} requires {sorted(missing)}")
    validate_locator(annotation["anchor"], where)
    validate_placement(annotation.get("placement", DEFAULT_PLACEMENT), where)
    if kind == "arrow":
        placement = annotation.get("placement", DEFAULT_PLACEMENT)
        demand(placement in ARROW_PLACEMENTS, f"{where}: placement {placement} does not apply to an arrow")
    if "from" in annotation:
        validate_locator(annotation["from"], where)


def validate_annotations(annotations: list[Spec], where: str) -> None:
    for index, annotation in enumerate(annotations, 1):
        validate_annotation(annotation, f"{where} annotation {index}")


def validate_figure(figure: Spec, index: int) -> None:
    slug = figure.get("slug", "")
    where = f"figure {index} ({slug})"
    demand(SLUG_PATTERN.fullmatch(slug), f"{where}: slug must be lowercase words joined by hyphens")
    demand("url" in figure, f"{where}: url is required")
    demand(figure.get("theme", "light") in THEMES, f"{where}: theme must be light or dark")
    validate_placement(figure.get("placement", DEFAULT_PLACEMENT), where)
    for name in FLAG_FIELDS:
        demand(isinstance(figure.get(name, False), bool), f"{where}: {name} must be true or false")
    demand(figure.get("login", True) in (True, False), f"{where}: login may only be false")
    validate_steps(figure.get("steps", []), where)
    validate_annotations(figure.get("annotations", []), where)
    validate_steps(figure.get("before_steps", []), f"{where} before")
    validate_annotations(figure.get("before_annotations", []), f"{where} before")


def validate_environment(spec: Spec) -> None:
    environment = str(spec.get("environment", "")).strip().lower()
    demand(environment, "spec: environment is required")
    demand(environment not in PRODUCTION_NAMES, f"spec: refusing to run against environment '{environment}'")
    demand(spec.get("base_url"), "spec: base_url is required")


def validate_login(login: Spec) -> None:
    demand(SLUG_PATTERN.fullmatch(login.get("name", "")), "login: name must be lowercase words joined by hyphens")
    demand(login.get("steps"), "login: steps are required")
    validate_steps(login["steps"], "login")
    demand("expect" in login, "login: expect is required, it proves the login worked")
    validate_locator(login["expect"], "login expect")


def validate_hide(hide: Any) -> None:
    valid = isinstance(hide, list) and all(isinstance(selector, str) for selector in hide)
    demand(valid, "spec: hide must be a list of selectors")


def validate_spec(spec: Spec) -> None:
    validate_environment(spec)
    validate_hide(spec.get("hide", []))
    validate_placement(spec.get("placement", DEFAULT_PLACEMENT), "spec")
    demand(spec.get("figures"), "spec: figures are required")
    for index, figure in enumerate(spec["figures"], 1):
        validate_figure(figure, index)
    if "login" in spec:
        validate_login(spec["login"])


def read_spec(path: Path) -> Spec:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as failure:
        raise CaptureFailure(f"cannot read spec {path}: {failure}") from failure


def text_query(target: Spec, text: str | None) -> tuple[str | re.Pattern[str] | None, bool]:
    kind = target.get("match", "exact")
    if kind == "regex":
        return (re.compile(text or ""), False)
    return (text, kind == "exact")


def locator_of(page: Page, target: Spec) -> Locator:
    if "selector" in target:
        return page.locator(target["selector"])
    if "role" in target:
        name, exact = text_query(target, target.get("name"))
        return page.get_by_role(target["role"], name=name, exact=exact)
    text, exact = text_query(target, target["text"])
    return page.get_by_text(text, exact=exact)


def single_visible(page: Page, target: Spec, where: str, timeout: int) -> Locator:
    locator = locator_of(page, target)
    description = describe_locator(target)
    try:
        locator.first.wait_for(state="visible", timeout=timeout)
    except PlaywrightTimeout as failure:
        raise CaptureFailure(f"{where}: {description} matched no visible element") from failure
    count = locator.count()
    demand(count == 1, f"{where}: {description} matched {count} elements, it must match exactly one")
    return locator


def secret_value(step: Spec, where: str) -> str:
    if "value" in step:
        return step["value"]
    name = step["value_env"]
    demand(name in os.environ, f"{where}: environment variable {name} is not set")
    return os.environ[name]


def open_url(page: Page, url: str, timeout: int) -> None:
    response = page.goto(url, timeout=timeout)
    if response is not None:
        demand(response.ok, f"{url} answered with status {response.status}")


def fill(page: Page, step: Spec, where: str, timeout: int) -> None:
    locator = single_visible(page, step["target"], where, timeout)
    literal = "value" in step and locator.get_attribute("type") == "password"
    demand(not literal, f"{where}: a password needs value_env, the spec is saved with the output")
    locator.fill(secret_value(step, where), timeout=timeout)


def perform(page: Page, step: Spec, base_url: str, where: str, timeout: int) -> None:
    kind = step["action"]
    if kind == "goto":
        open_url(page, urljoin(base_url, step["url"]), timeout)
    elif kind == "fill":
        fill(page, step, where, timeout)
    elif kind == "click":
        single_visible(page, step["target"], where, timeout).click(timeout=timeout)
    elif kind == "hover":
        single_visible(page, step["target"], where, timeout).hover(timeout=timeout)
    elif kind == "press":
        press(page, step, where, timeout)
    elif "milliseconds" in step:
        page.wait_for_timeout(step["milliseconds"])
    else:
        single_visible(page, step["target"], where, timeout)


def press(page: Page, step: Spec, where: str, timeout: int) -> None:
    if "target" in step:
        single_visible(page, step["target"], where, timeout).press(step["key"], timeout=timeout)
    else:
        page.keyboard.press(step["key"])


def run_steps(page: Page, steps: list[Spec], base_url: str, where: str, timeout: int) -> None:
    for index, step in enumerate(steps, 1):
        location = f"{where} step {index} ({step['action']})"
        try:
            perform(page, step, base_url, location, timeout)
        except PlaywrightError as failure:
            first_line = str(failure).splitlines()[0]
            raise CaptureFailure(f"{location}: {first_line}") from failure


def wait_idle(page: Page) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=IDLE_LIMIT)
    except PlaywrightTimeout:
        return


def settle(page: Page, where: str, timeout: int) -> None:
    wait_idle(page)
    settled = page.evaluate(SETTLE_SCRIPT, timeout)
    demand(settled, f"{where}: animations did not finish within {timeout} ms")


def measure(locator: Locator, target: Spec, where: str) -> Box:
    values = locator.evaluate(MEASURE_SCRIPT)
    demand(values, f"{where}: {describe_locator(target)} is scrolled or clipped out of view")
    box = Box(**values)
    demand(box.width > 0 and box.height > 0, f"{where}: {describe_locator(target)} has no size")
    return box


def anchors_of(annotation: Spec) -> list[Spec]:
    return [annotation[key] for key in ("anchor", "from") if key in annotation]


def stable_boxes(page: Page, pairs: list[tuple[Spec, Locator]], where: str, timeout: int) -> list[Box]:
    previous: list[Box] | None = None
    for _ in range(max(2, timeout // STABLE_POLL)):
        current = [measure(locator, target, where) for target, locator in pairs]
        if current == previous:
            return current
        previous = current
        page.wait_for_timeout(STABLE_POLL)
    raise CaptureFailure(f"{where}: anchors keep moving, geometry is not stable")


def clamp_frame(box: Box, page_size: Spec) -> Box:
    left = max(EDGE_MARGIN, box.x - BOX_PADDING)
    top = max(EDGE_MARGIN, box.y - BOX_PADDING)
    right = min(page_size["width"] - EDGE_MARGIN, box.right + BOX_PADDING)
    bottom = min(page_size["height"] - EDGE_MARGIN, box.bottom + BOX_PADDING)
    return Box(left, top, right - left, bottom - top)


def removed_place(box: Box, annotation: Spec) -> Box:
    offset = annotation["offset"]
    return Box(
        box.x + offset.get("x", 0),
        box.y + offset.get("y", 0),
        offset.get("width", box.width),
        offset.get("height", box.height),
    )


def default_tail(box: Box, page_size: Spec) -> tuple[float, float]:
    center_x, center_y = box.center
    reach_x = box.width / 2 + ARROW_REACH[0]
    reach_y = box.height / 2 + ARROW_REACH[1]
    x = center_x - reach_x if center_x - reach_x >= 0 else center_x + reach_x
    y = center_y - reach_y if center_y - reach_y >= 0 else center_y + reach_y
    return (min(x, page_size["width"]), min(y, page_size["height"]))


def arrow_tail(box: Box, source: Box | None, annotation: Spec, page_size: Spec) -> tuple[float, float]:
    if source is not None:
        return source.center
    if "offset" in annotation:
        offset = annotation["offset"]
        center_x, center_y = box.center
        return (center_x + offset.get("x", 0), center_y + offset.get("y", 0))
    return default_tail(box, page_size)


def arrow_tip(box: Box, tail: tuple[float, float], where: str) -> tuple[float, float]:
    center_x, center_y = box.center
    delta_x, delta_y = tail[0] - center_x, tail[1] - center_y
    half_width, half_height = box.width / 2 + BOX_PADDING, box.height / 2 + BOX_PADDING
    scale = min(
        half_width / abs(delta_x) if delta_x else math.inf,
        half_height / abs(delta_y) if delta_y else math.inf,
    )
    demand(scale < 1, f"{where}: arrow starts inside its target")
    return (center_x + delta_x * scale, center_y + delta_y * scale)


def inside_page(box: Box, page_size: Spec) -> bool:
    return box.inside(0, 0, page_size["width"], page_size["height"])


def geometry(kind: str, box: Box, source: Box | None, annotation: Spec, page_size: Spec, where: str) -> Spec:
    if kind == "removed":
        place = removed_place(box, annotation)
        demand(inside_page(place, page_size), f"{where}: removed marker falls outside the page")
        frame = clamp_frame(place, page_size)
        return {"rectangle": asdict(frame), "corner": {"x": frame.x, "y": frame.y}, "bottom": frame.bottom}
    frame = clamp_frame(box, page_size)
    corner = {"x": frame.x, "y": frame.y}
    result: Spec = {"rectangle": asdict(frame), "corner": corner, "bottom": frame.bottom}
    if kind == "arrow":
        tail = arrow_tail(box, source, annotation, page_size)
        demand(
            0 <= tail[0] <= page_size["width"] and 0 <= tail[1] <= page_size["height"],
            f"{where}: arrow starts outside the page",
        )
        tip = arrow_tip(box, tail, where)
        result |= {"tail": {"x": tail[0], "y": tail[1]}, "tip": {"x": tip[0], "y": tip[1]}}
        result["corner"] = {"x": tail[0], "y": tail[1]}
        result["bottom"] = tail[1]
    return result


def clamped_badge(corner: Spec, page_size: Spec) -> Spec:
    return {
        "x": max(BADGE_MARGIN, min(page_size["width"] - BADGE_MARGIN, corner["x"])),
        "y": max(BADGE_MARGIN, min(page_size["height"] - BADGE_MARGIN, corner["y"])),
    }


def outside_badge(placement: str, frame: Box, page_size: Spec, where: str) -> Spec:
    middle_x, middle_y = frame.center
    x, y = {
        "left": (frame.x - BADGE_REACH, middle_y),
        "right": (frame.right + BADGE_REACH, middle_y),
        "above": (middle_x, frame.y - BADGE_REACH),
        "below": (middle_x, frame.bottom + BADGE_REACH),
    }[placement]
    fits = BADGE_MARGIN <= x <= page_size["width"] - BADGE_MARGIN and BADGE_MARGIN <= y <= page_size["height"] - BADGE_MARGIN
    demand(fits, f"{where}: badge placed {placement} falls outside the page")
    return {"x": x, "y": y}


def inside_badge(frame: Box, where: str) -> Spec:
    fits = frame.width >= 2 * BADGE_INSET and frame.height >= 2 * BADGE_INSET
    demand(fits, f"{where}: shape is too small for a number placed inside")
    return {"x": frame.x + BADGE_INSET, "y": frame.y + BADGE_INSET}


def corner_point(placement: str, frame: Box) -> Spec:
    return {
        "top-right": {"x": frame.right, "y": frame.y},
        "bottom-left": {"x": frame.x, "y": frame.bottom},
        "bottom-right": {"x": frame.right, "y": frame.bottom},
    }[placement]


def badge_center(placement: str, shape: Spec, page_size: Spec, where: str) -> Spec:
    frame = Box(**shape["rectangle"])
    if placement in TAIL_PLACEMENTS:
        return clamped_badge(shape["corner"], page_size)
    if placement in OUTSIDE_PLACEMENTS:
        return outside_badge(placement, frame, page_size, where)
    if placement == "inside":
        return inside_badge(frame, where)
    return clamped_badge(corner_point(placement, frame), page_size)


def build_mark(annotation: Spec, box: Box, source: Box | None, page_size: Spec, where: str) -> Spec:
    kind = annotation["kind"]
    shape = geometry(kind, box, source, annotation, page_size, where)
    placement = annotation.get("placement", DEFAULT_PLACEMENT)
    badge = badge_center(placement, shape, page_size, where) if annotation.get("number") is not None else None
    return {
        "kind": kind,
        "number": annotation.get("number"),
        "text": annotation.get("text"),
        "anchor_description": describe_locator(annotation["anchor"]),
        "element": asdict(box),
        "badge": badge,
        **shape,
    }


def collect_pairs(page: Page, annotations: list[Spec], where: str, timeout: int) -> list[tuple[Spec, Locator]]:
    pairs: list[tuple[Spec, Locator]] = []
    for annotation in annotations:
        for target in anchors_of(annotation):
            locator = single_visible(page, target, where, timeout)
            locator.scroll_into_view_if_needed(timeout=timeout)
            pairs.append((target, locator))
    return pairs


def build_marks(annotations: list[Spec], boxes: list[Box], page_size: Spec, where: str) -> list[Spec]:
    remaining = iter(boxes)
    marks: list[Spec] = []
    for annotation in annotations:
        box = next(remaining)
        source = next(remaining) if "from" in annotation else None
        marks.append(build_mark(annotation, box, source, page_size, where))
    return marks


def check_viewport(marks: list[Spec], page_size: Spec, where: str) -> None:
    left, top = page_size["left"], page_size["top"]
    right, bottom = left + page_size["viewportWidth"], top + page_size["viewportHeight"]
    for mark in marks:
        element = Box(**mark["element"])
        demand(element.inside(left, top, right, bottom), f"{where}: {mark['anchor_description']} is outside the viewport, use full_page")


def hide_elements(page: Page, selectors: list[str]) -> None:
    for selector in selectors:
        page.locator(selector).evaluate_all(HIDE_SCRIPT)


def annotate(page: Page, annotations: list[Spec], full_page: bool, hide: list[str], where: str, timeout: int) -> tuple[list[Spec], Spec]:
    hide_elements(page, hide)
    settle(page, where, timeout)
    pairs = collect_pairs(page, annotations, where, timeout)
    if full_page:
        page.evaluate(SCROLL_TOP_SCRIPT)
    settle(page, where, timeout)
    boxes = stable_boxes(page, pairs, where, timeout)
    page_size = page.evaluate(PAGE_SCRIPT)
    marks = build_marks(annotations, boxes, page_size, where)
    if not full_page:
        check_viewport(marks, page_size, where)
    page.evaluate(DRAW_SCRIPT, {"marks": marks, "page": page_size})
    return marks, page_size


def locale_option(spec: Spec) -> Spec:
    return {"locale": spec["locale"]} if "locale" in spec else {}


def context_options(spec: Spec, figure: Spec, options: Options, state: Path | None) -> Spec:
    viewport = {**DEFAULT_VIEWPORT, **figure.get("viewport", {})}
    result: Spec = {
        "viewport": {"width": viewport["width"], "height": viewport["height"]},
        "device_scale_factor": viewport["scale"],
        "color_scheme": figure.get("theme", "light"),
        "ignore_https_errors": options.ignore_https,
        "has_touch": figure.get("has_touch", False),
        "reduced_motion": "reduce" if figure.get("reduced_motion", False) else "no-preference",
        **locale_option(spec),
    }
    if state is not None:
        result["storage_state"] = str(state)
    return result


def login_identity(spec: Spec) -> str:
    login = spec["login"]
    resolved = [os.environ.get(step["value_env"]) for step in login["steps"] if "value_env" in step]
    text = json.dumps([spec["base_url"], login, resolved], sort_keys=True)
    return hashlib.sha256(text.encode()).hexdigest()[:IDENTITY_LENGTH]


def state_path(spec: Spec, options: Options) -> Path:
    return options.state_directory / f"{spec['login']['name']}-{login_identity(spec)}.json"


def landing_path(state: Path) -> Path:
    return state.with_suffix(".landing")


def prepare_state_directory(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    ignore = directory / ".gitignore"
    if not ignore.exists():
        ignore.write_text("*\n")


def save_state(context: BrowserContext, page: Page, path: Path) -> None:
    prepare_state_directory(path.parent)
    context.storage_state(path=str(path))
    path.chmod(0o600)
    landing = landing_path(path)
    landing.write_text(page.url)
    landing.chmod(0o600)


def failure_picture(page: Page, name: str, options: Options) -> Path | None:
    path = options.output / FAILURES_NAME / f"{name}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        page.screenshot(path=str(path), full_page=True, animations="disabled", timeout=options.timeout)
    except PlaywrightError:
        return None
    return path


@contextmanager
def picture_on_failure(page: Page, name: str, where: str, options: Options) -> Iterator[None]:
    try:
        yield
    except CaptureFailure as failure:
        raise CaptureFailure(with_picture(str(failure), page, name, options)) from failure
    except PlaywrightError as failure:
        first_line = str(failure).splitlines()[0]
        raise CaptureFailure(with_picture(f"{where}: {first_line}", page, name, options)) from failure


def with_picture(message: str, page: Page, name: str, options: Options) -> str:
    picture = failure_picture(page, name, options)
    return f"{message} (page at failure: {picture})" if picture else message


def log_in(browser: Browser, spec: Spec, options: Options, path: Path) -> None:
    login = spec["login"]
    context = browser.new_context(ignore_https_errors=options.ignore_https, **locale_option(spec))
    try:
        page = context.new_page()
        with picture_on_failure(page, "login", "login", options):
            run_steps(page, login["steps"], spec["base_url"], "login", options.timeout)
            single_visible(page, login["expect"], "login expect", options.timeout)
            save_state(context, page, path)
    finally:
        context.close()


def session_alive(browser: Browser, spec: Spec, options: Options, path: Path) -> bool:
    landing = landing_path(path)
    if not path.exists() or not landing.exists():
        return False
    try:
        context = browser.new_context(ignore_https_errors=options.ignore_https, storage_state=str(path), **locale_option(spec))
    except PlaywrightError:
        return False
    try:
        page = context.new_page()
        open_url(page, landing.read_text(), options.timeout)
        single_visible(page, spec["login"]["expect"], "login expect", options.timeout)
        return True
    except (CaptureFailure, PlaywrightError):
        return False
    finally:
        context.close()


def ensure_login(browser: Browser, spec: Spec, options: Options, fresh: bool) -> Path:
    path = state_path(spec, options)
    if fresh or not session_alive(browser, spec, options, path):
        log_in(browser, spec, options, path)
    return path


def shots_of(figure: Spec) -> list[Shot]:
    current = Shot(figure["slug"], figure["url"], figure.get("steps", []), figure.get("annotations", []), figure, "current")
    if "before_url" not in figure:
        return [current]
    before = Shot(
        f"{figure['slug']}-before",
        figure["before_url"],
        figure.get("before_steps", []),
        figure.get("before_annotations", []),
        figure,
        "before",
    )
    return [before, current]


def figure_name(number: int, slug: str) -> str:
    return f"{number:02d}-{slug}.png"


def inherited_placement(annotation: Spec, default: str) -> str:
    if annotation["kind"] == "arrow" and default not in ARROW_PLACEMENTS:
        return DEFAULT_PLACEMENT
    return default


def with_placements(spec: Spec, shot: Shot) -> list[Spec]:
    default = shot.figure.get("placement", spec.get("placement", DEFAULT_PLACEMENT))
    return [
        {"placement": inherited_placement(annotation, default), **annotation}
        for annotation in shot.annotations
    ]


def capture_shot(browser: Browser, spec: Spec, shot: Shot, number: int, options: Options, state: Path | None, staging: Path) -> Spec:
    where = f"figure {shot.slug}"
    full_page = shot.figure.get("full_page", True)
    context = browser.new_context(**context_options(spec, shot.figure, options, state))
    hide = spec.get("hide", [])
    try:
        page = context.new_page()
        with picture_on_failure(page, shot.slug, where, options):
            open_url(page, urljoin(spec["base_url"], shot.url), options.timeout)
            run_steps(page, shot.steps, spec["base_url"], where, options.timeout)
            marks, page_size = annotate(page, with_placements(spec, shot), full_page, hide, where, options.timeout)
            hide_elements(page, hide)
            name = figure_name(number, shot.slug)
            page.screenshot(path=str(staging / name), full_page=full_page, animations="disabled", timeout=options.timeout)
            return manifest_entry(shot, number, name, page, marks, page_size)
    finally:
        context.close()


def manifest_entry(shot: Shot, number: int, name: str, page: Page, marks: list[Spec], page_size: Spec) -> Spec:
    warnings = [f"{len(marks)} marks, keep one idea per image"] if len(marks) > MARK_ADVICE else []
    return {
        "number": number,
        "file": f"figures/{name}",
        "slug": shot.slug,
        "role": shot.role,
        "url": page.url,
        "viewport": {**DEFAULT_VIEWPORT, **shot.figure.get("viewport", {})},
        "theme": shot.figure.get("theme", "light"),
        "page": {"width": page_size["width"], "height": page_size["height"]},
        "marks": marks,
        "warnings": warnings,
    }


def uses_login(spec: Spec, shot: Shot) -> bool:
    return "login" in spec and shot.figure.get("login", True)


def capture_all(browser: Browser, spec: Spec, options: Options, staging: Path) -> list[Spec]:
    shots = [shot for figure in spec["figures"] for shot in shots_of(figure)]
    fresh = options.fresh_login
    entries: list[Spec] = []
    for number, shot in enumerate(shots, 1):
        state = None
        if uses_login(spec, shot):
            state = ensure_login(browser, spec, options, fresh)
            fresh = False
        entries.append(capture_shot(browser, spec, shot, number, options, state, staging))
    return entries


def launch(playwright: Any) -> Browser:
    try:
        return playwright.chromium.launch()
    except PlaywrightError as failure:
        raise CaptureFailure(
            f"cannot start Chromium, try: uv run --with playwright=={PLAYWRIGHT_VERSION} playwright install chromium"
        ) from failure


def publish(staging: Path, figures: Path, entries: list[Spec], spec: Spec) -> None:
    figures.mkdir(parents=True, exist_ok=True)
    for old in figures.iterdir():
        if FIGURE_PATTERN.fullmatch(old.name) or old.name in (MANIFEST_NAME, SPEC_NAME):
            old.unlink()
    for new in staging.iterdir():
        shutil.move(str(new), figures / new.name)
    manifest = {"environment": spec["environment"], "base_url": spec["base_url"], "figures": entries}
    (figures / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    (figures / SPEC_NAME).write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n")


def run(spec_path: Path, options: Options) -> list[Spec]:
    spec = read_spec(spec_path)
    validate_spec(spec)
    options.output.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(options.output / FAILURES_NAME, ignore_errors=True)
    with tempfile.TemporaryDirectory(dir=options.output, prefix=".capture-") as directory:
        staging = Path(directory)
        with sync_playwright() as playwright:
            browser = launch(playwright)
            try:
                entries = capture_all(browser, spec, options, staging)
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
    options = Options(arguments.out, arguments.state_dir, arguments.ignore_https_errors, arguments.fresh_login, arguments.timeout)
    try:
        entries = run(arguments.spec, options)
    except CaptureFailure as failure:
        print(f"error: {failure}", file=sys.stderr)
        return 1
    for entry in entries:
        print(entry["file"])
        for warning in entry["warnings"]:
            print(f"warning: {entry['file']}: {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
