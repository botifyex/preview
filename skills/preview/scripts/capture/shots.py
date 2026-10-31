from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import Browser, Page

from capture.annotate import annotate, hide_elements
from capture.constants import ARROW_PLACEMENTS, DEFAULT_PLACEMENT, DEFAULT_VIEWPORT, MARK_ADVICE
from capture.failures import picture_on_failure
from capture.model import Options, Shot, Spec
from capture.session import ensure_login, locale_option
from capture.steps import open_url, run_steps


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


def shots_of(figure: Spec) -> list[Shot]:
    current = Shot(
        figure["slug"], figure["url"], figure.get("steps", []), figure.get("annotations", []), figure, "current"
    )
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


def all_shots(spec: Spec) -> list[Shot]:
    return [shot for figure in spec["figures"] for shot in shots_of(figure)]


def planned_names(spec: Spec) -> list[str]:
    return [figure_name(number, shot.slug) for number, shot in enumerate(all_shots(spec), 1)]


def inherited_placement(annotation: Spec, default: str) -> str:
    if annotation["kind"] == "arrow" and default not in ARROW_PLACEMENTS:
        return DEFAULT_PLACEMENT
    return default


def with_placements(spec: Spec, shot: Shot) -> list[Spec]:
    default = shot.figure.get("placement", spec.get("placement", DEFAULT_PLACEMENT))
    return [{"placement": inherited_placement(annotation, default), **annotation} for annotation in shot.annotations]


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


def capture_shot(
    browser: Browser, spec: Spec, shot: Shot, number: int, options: Options, state: Path | None, staging: Path
) -> Spec:
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
            page.screenshot(
                path=str(staging / name), full_page=full_page, animations="disabled", timeout=options.timeout
            )
            return manifest_entry(shot, number, name, page, marks, page_size)
    finally:
        context.close()


def uses_login(spec: Spec, shot: Shot) -> bool:
    return "login" in spec and shot.figure.get("login", True)


def capture_all(browser: Browser, spec: Spec, options: Options, staging: Path) -> list[Spec]:
    shots = all_shots(spec)
    fresh = options.fresh_login
    entries: list[Spec] = []
    for number, shot in enumerate(shots, 1):
        state = None
        if uses_login(spec, shot):
            state = ensure_login(browser, spec, options, fresh)
            fresh = False
        entries.append(capture_shot(browser, spec, shot, number, options, state, staging))
    return entries
