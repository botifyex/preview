# Capture spec

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/run_capture.py" <spec.json> --out <dir> [--state-dir <dir>] [--ignore-https-errors] [--fresh-login] [--timeout <ms>]
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `--out` | required | Writes `<dir>/figures/` |
| `--state-dir` | `$XDG_CACHE_HOME/preview/state`, else `~/.cache/preview/state` | Saved login sessions, outside the target repository. A `*` `.gitignore` is written inside; a new directory is mode 700, files are mode 600 from before anything is written |
| `--ignore-https-errors` | off | For local certificates only |
| `--fresh-login` | off | Log in again even if the saved session still works |
| `--timeout` | 10000 | Milliseconds for each wait |

## Spec

```json
{
  "environment": "local",
  "base_url": "https://localhost:8443",
  "locale": "ru-RU",
  "hide": ["nextjs-portal"],
  "login": {
    "name": "preview-user",
    "steps": [
      { "action": "goto", "url": "/login" },
      { "action": "fill", "target": { "role": "textbox", "name": "Email" }, "value": "preview-1730@example.com" },
      { "action": "fill", "target": { "role": "textbox", "name": "Password" }, "value_env": "PREVIEW_PASSWORD" },
      { "action": "click", "target": { "role": "button", "name": "Sign in" } }
    ],
    "expect": { "role": "heading", "name": "Dashboard" }
  },
  "figures": [
    {
      "slug": "export-button",
      "url": "/reports",
      "viewport": { "width": 1280, "height": 800, "scale": 1 },
      "theme": "light",
      "full_page": true,
      "steps": [
        { "action": "click", "target": { "text": "March" } },
        { "action": "wait", "target": { "selector": ".report-table" } }
      ],
      "annotations": [
        { "kind": "box", "anchor": { "role": "button", "name": "Export" }, "number": 1, "text": "New button" }
      ]
    }
  ]
}
```

Top level: `environment` and `base_url` are required, and `production`, `prod` or `live`
is refused. `locale`, `hide`, `login`, `placement` and `color` are optional. `figures` is required. Relative URLs
are resolved against `base_url`.

**Hide** lists selectors of things that are not part of the product, such as development
overlays. They get `display: none` before measuring and again before the screenshot. A selector
matching nothing is fine, so one spec works on any build. Selectors reach into open shadow roots;
hiding the host also covers closed ones. For the Next.js development indicator use
`nextjs-portal`, the host of its shadow root. Never hide anything to make a page look better.

**Login** uses the same steps as figures. `expect` must appear afterwards or the run fails,
so a failed login cannot produce pictures of a login form. The session file is
`<name>-<hash>.json`, where the hash covers `base_url`, the whole login block and the values of
its `value_env` variables: a different user never reuses another's session. Before each figure
that uses the session, the page reached after login is reopened and `expect` checked there; if
it fails (expired, or signed out by an earlier step), the login runs again.

**Figure**: `slug` (lowercase words with hyphens) and `url` are required. `viewport` defaults
to 1280x800 at scale 1. `theme` is `light` or `dark`. `full_page` defaults to true; with
`false`, everything drawn must lie inside the viewport or the run fails: each anchor and `from`
element, frame, ellipse, arrow tail and tip, ends of an underline, connector or leader, callout block,
number and label. There, frames, a default arrow tail, labels and
`corner` or `top-left` numbers keep to the visible rectangle, so they fit whenever the anchor does;
an explicit `offset`, `from` or other placement falling outside fails. `has_touch: true` and
`reduced_motion: true` set those browser features. `login: false` keeps a figure signed out in
a run that has a `login`; if every figure does so, no login happens. `false` is its only value. `placement` and `color` set a default for its marks, see Annotations.

## Locators

Used for `target` and `anchor`. Exactly one of the three kinds:

- `{ "selector": "#save" }`: CSS
- `{ "role": "button", "name": "Save" }`: role with an exact name; `name` is optional
- `{ "text": "Save" }`: exact visible text

Text and role `name` compare exactly by default. Add `"match": "substring"` (ignores case) or
`"match": "regex"`: `{ "text": "^Add .* task$", "match": "regex" }`.

Must match exactly one visible element. No match or several matches is a failure naming the
locator. Prefer role and text: they survive restyling and describe what the user sees.
Elements inside iframes are not supported.

## Steps

| `action` | Fields | Meaning |
| --- | --- | --- |
| `goto` | `url` | Open a page. A status of 400 or above fails |
| `fill` | `target`, then `value` or `value_env` | Type. `value_env` reads an environment variable and fails when it is unset. A password field refuses a literal `value` |
| `click` | `target` | Click |
| `hover` | `target` | Move the mouse over it. The state lasts while the element stays under the mouse: use `full_page: false` if the page must scroll |
| `press` | `key`, optional `target` | Press a key |
| `wait` | `target` or `milliseconds` | Wait for an element or a time |

The figure's `url` opens first, then its steps run. Values are never written to the manifest,
but the spec is saved with the output as written, so keep every secret in `value_env`, including
ones outside password fields and in URLs.

## Annotations

| `kind` | Required | Draws |
| --- | --- | --- |
| `box` | `anchor` | Solid rectangle 4 px outside the element |
| `arrow` | `anchor` | Arrow to the element's edge. Starts at `from` (a locator's centre), or at `offset` from the element's centre, or else diagonally at a free side |
| `badge` | `anchor`, `number` | Numbered circle at the top left corner |
| `label` | `anchor`, `text` | Text tag above the element, or below when there is no room |
| `removed` | `anchor`, `offset` | Dashed rectangle in a separate red, at the anchor's box moved by `offset.x`, `offset.y`, sized `offset.width`, `offset.height` or as the anchor |
| `callout` | `anchor`, `text` | Block of white text on the mark's colour, wrapped to `width`, with a leader line to the anchor's edge. Optional `side`, see below |
| `ellipse` | `anchor` | Ellipse through the corners of the rectangle 4 px outside the element, so it crosses none of the element; it reaches about 21% of the rectangle's size further on each side |
| `underline` | `anchor` | Line under the element, 4 px below it and as wide as it |
| `highlight` | `anchor` | Translucent fill over the rectangle 4 px outside the element, opacity 0.25 and no frame |
| `spotlight` | `anchor` | Dims everything outside the rectangle 4 px outside the element, opacity 0.6, with a thin white rim. At most one per image; always drawn under the other marks, as `highlight` is. Only its number and label take `color` |
| `connector` | `anchor`, `from` | Line between the edges of the two elements. Optional `heads`: `none` (default), `end` (at the anchor) or `both` |

`box`, `arrow`, `removed`, `ellipse`, `underline`, `highlight`, `spotlight`, `connector` also accept
`number` and `text`; `callout` accepts `number`, and its `text` is the block. The opacities are
fixed. `side`, `width` and `heads` on any other kind fail.

`callout` wraps with text measured by the browser, at spaces, at a line break you write, and inside
a word longer than the width. `width` is the widest the block may be, from 80, by default 280 or
what the page leaves. `side` is `left`, `right`, `above` or `below`; without it the first of these,
in this order, that fits inside the page (the viewport for `full_page: false`). The block keeps
28 px from the anchor's rectangle, so it never covers its anchor, but it may cover the anchor's
neighbours: open the image, and set `side` if it does.

`placement` chooses where a mark's number sits. It can be set on the annotation, the figure or
the top level of the spec; the nearest wins, and with none it is `corner`. An invalid value fails
and names its level. It has no effect on a mark without a `number`.

| `placement` | Number sits | Applies to |
| --- | --- | --- |
| `corner`, `top-left` | On the top left corner; on the tail for an arrow; for a connector on the line, halfway between the two elements' centres | all |
| `top-right`, `bottom-left`, `bottom-right` | On that corner | all but arrows and connectors |
| `inside` | Fully inside, at the top left. A shape under 36 px in width or height fails | all but arrows, connectors and callouts |
| `left`, `right`, `above`, `below` | Fully outside, 20 px from that side. Off the page fails | all; for an arrow or connector, beside its target |

The shape is the drawn rectangle: the element plus 4 px, the `removed` place, or a callout's block.
`badge`, `label`, `underline` and `connector` draw no rectangle and use the same one. An `ellipse`
passes through that rectangle's corners, so a corner number sits on the curve, and an outside number
keeps 20 px from the curve. An arrow or connector has no inside or corners of its own, and a number
inside a callout would cover its text, so naming one of those on the annotation fails; inherited from
the figure or spec, it falls back to the `corner` row. A callout's number over its own anchor fails.
Corner placements are moved back onto the page at its edges.

`color` is the colour of a mark as `#RRGGBB`, in either case: frame, arrow, line, fill, number circle,
label and callout back. The white halo and white text stay. It can be set on the annotation, the figure or the top
level of the spec; the nearest wins, and with none it is `#E6004C`. A `removed` mark is `#C81E1E`
and takes only a `color` written on itself, so a figure or spec colour leaves removals distinguishable.
An invalid value fails and names its level.

Failures rather than guesses:
an arrow starting inside its target or outside the page, a `removed` place outside the page,
a label wider than the page, anchors that keep moving, a callout that fits on no side or not on its
`side` (naming the anchor), a connector between elements that touch or overlap.

A malformed spec fails with `error: ...` before the browser starts: wrong types for any field,
non-integer `number`, `text` or `name` not a string, a `color` other than `#RRGGBB`, numbers beyond 1000000000 or not finite,
an empty callout `text`, a callout `width` under 80, an unknown `side` or `heads`, a second `spotlight` in one image,
`milliseconds` below 0, `offset.width`, `offset.height` or a viewport size of 0 or less.

## What happens before drawing

Fonts are awaited and network idle is given up to 3 s. Finite animations finish (a failure
after the timeout); endless ones are cancelled so they rest at their base position. Each
anchor is scrolled into view so lazy content loads and inner panels scroll, then a full-page
figure returns to the top. Boxes are measured until two readings agree, and a box is cut to
what its scrolling ancestors leave visible. The overlay is one SVG at document coordinates.

## Before images

```json
{
  "slug": "old-sidebar",
  "url": "/reports",
  "before_url": "http://localhost:9000/reports",
  "before_steps": [],
  "before_annotations": [{ "kind": "box", "anchor": { "text": "Old filter" }, "number": 1 }],
  "annotations": [{ "kind": "removed", "anchor": { "role": "navigation" }, "offset": { "y": 60 }, "number": 1 }]
}
```

`before_url` must point at a running old version. It produces its own numbered figure right
before the current one: `03-old-sidebar-before.png`, `04-old-sidebar.png`. Sessions are per
host, so an old version on another address must log in through `before_steps`. `placement` and
`color` reach `before_annotations` through the same chain.

## Schemes

A figure with `panels` in place of `url` combines several captures into one image: a complex page in
parts, a step-by-step path, links between screens. It yields exactly one numbered `NN-slug.png`, so
numbering, publishing and the report rules are those of any figure. Panels are captured into a
private temporary directory and never published alone.

```json
{
  "slug": "reach-export",
  "viewport": { "width": 1024, "height": 640 },
  "steps_numbers": true,
  "links": "sequence",
  "panels": [
    { "url": "/", "title": "Open Reports", "annotations": [{ "kind": "box", "anchor": { "text": "Reports" }, "number": 1 }] },
    { "url": "/reports", "title": "Pick a month", "crop": { "selector": ".months" } },
    { "url": "/reports/march", "title": "Press Export" }
  ]
}
```

| Figure field | Default | Meaning |
| --- | --- | --- |
| `panels` | required | Non-empty list. `url`, `before_url`, `before_steps`, `before_annotations`, `steps`, `annotations`, `full_page` on the figure itself are refused |
| `layout` | `row` | `row`, `column`, or `grid`, which requires `columns`. `columns` without a grid is refused |
| `panel_width` | 640 | CSS pixels. Scales a panel's picture down, never up |
| `gap` | 32, or 72 with links | Pixels between panels. By default it also widens to fit the longest link text |
| `background` | `#F2F4F7` | `#RRGGBB`. Titles turn white on a dark one |
| `steps_numbers` | false | Number panel titles 1, 2, 3 for a path; a panel without a title still gets its number |
| `links` | none | A list, see below, or `"sequence"` in a row or column: each panel to the next |
| `continuous` | false | One browser context and page for all panels, in order: see below |

`viewport`, `theme`, `login`, `has_touch`, `reduced_motion`, `placement` and `color` on the figure
are defaults for its panels, and a panel's `viewport` overrides the figure's field by field. `color` also colours links and step numbers.

**Panel**: `url`, plus `steps`, `annotations`, `viewport`, `theme`, `login`, `has_touch`,
`reduced_motion`, `placement`, `color` and `full_page` as for a figure, except that `full_page`
defaults to false. Also `title`, text above the panel (a long title widens the panel's frame),
`crop`, a locator that keeps only that element plus `crop_padding` (default 16) on each side, and
`id`, a slug for links, otherwise the panel's 1-based index. A crop that does not fit the picture, or
marks reaching past the crop, fail: a number on a cropped element's corner needs `crop_padding` of
about 20. A spotlight's dimming covers the whole picture and does not count as reaching past the
crop; its hole, number and label do. A connector with an element entirely outside the crop also
fails. A spotlight is limited to one per panel. Failures name `figure <slug> panel <n>`, and the
page at failure is saved as `failures/<slug>-panel-<n>.png`.

**Each panel starts fresh by default**: its own browser context, with no cookies, storage, clicks or
page from the panel before. A cart filled in panel 1 is empty in panel 2, and nothing warns about it.
For a path where one step depends on the last, set `"continuous": true`. All panels then share one
context and page, in panel order. A panel's `url` is optional, except on the first: given, it
navigates; absent, the page stays where the last panel left it. Its `steps` run, then it is
captured. A panel's marks and `hide` are undone before the next panel's steps. `viewport`, `theme`,
`has_touch`, `reduced_motion` and `login` on a panel are refused, set them on the figure. Login works
as for a figure.

**Link**: `{ "from": <panel id>, "to": <panel id>, "text": "...", "from_mark": 2, "style": "dashed" }`.
`from` and `to` are required; `style` is `solid` (default) or `dashed`. The arrow runs edge to edge
through the gaps and margins, with up to two bends, and never over a panel, including its title.
`from_mark` starts it on that numbered mark, in the from panel; the arrow may cross only that panel,
and a mark without that number, or a number used twice in that panel, fails. These fail rather than draw something false: a link that
cannot be routed (panels touching on every side), and a `text` that fits nowhere beside its arrow.

Numbers of marks are redrawn at a readable size on top of a scaled panel, at least 10 px in radius.
Other marks, and the page itself, scale with the panel: with a small `panel_width`, labels get hard to read.

A picture over 8000 px on a side, in image pixels, fails with `error: ...`. More than 6 panels, or
more than 5 marks in a panel, gives a warning. Wrong types, unknown panels in a link, duplicate `id`s
and missing marks fail before the browser starts.

The manifest entry has `number`, `file`, `slug`, `role: "scheme"`, `layout`, `continuous`, `viewport` (the size of
the composite in CSS pixels and its `scale`, the highest of its panels), `warnings`, and:

- `panels`: each with `id`, `title`, `url` (where the panel really ended), `rectangle` (the picture drawn, in the composite), `scale`
  and `marks` in composite coordinates: every point, rectangle, `top` and `bottom` is scaled and
  shifted, a spotlight's `veil` is a size and only scaled, and `opacity` and the `text` of `lines` stay;
- `links`: each with `from`, `to`, `style`, `text`, `from_mark`, `tail`, `tip`, `points` (the whole
  line) and `label` (the text's rectangle, or `null`).

## Manifest

`<out>/figures/manifest.json`:

```json
{
  "environment": "local",
  "base_url": "https://localhost:8443",
  "figures": [
    {
      "number": 1,
      "file": "figures/01-export-button.png",
      "slug": "export-button",
      "role": "current",
      "url": "https://localhost:8443/reports",
      "viewport": { "width": 1280, "height": 800, "scale": 1 },
      "theme": "light",
      "page": { "width": 1280, "height": 1900 },
      "marks": [
        {
          "kind": "box",
          "color": "#E6004C",
          "number": 1,
          "text": "New button",
          "anchor_description": "{\"name\": \"Export\", \"role\": \"button\"}",
          "element": { "x": 300, "y": 200, "width": 160, "height": 48 },
          "rectangle": { "x": 296, "y": 196, "width": 168, "height": 56 },
          "corner": { "x": 296, "y": 196 },
          "bottom": 252,
          "badge": { "x": 296, "y": 196 }
        }
      ],
      "warnings": []
    }
  ]
}
```

`role` is `current`, `before` or, see Schemes, `scheme`. `element` is the measured box in CSS pixels of the document,
`rectangle` the drawn one, `badge` the centre of the number, `null` without a number, `color` the
colour drawn, in capitals. Arrows add `tail` and `tip`. Underlines add `start` and `end`. An ellipse
adds `bounds`, the box of its curve. `highlight` and `spotlight` add `opacity`, and `spotlight` adds
`veil`, the size of the dimmed area. A connector adds `start` at `from`, `end` at the anchor, `source`
(the `from` element) and `heads`. A callout's `rectangle` is its block; it adds `side`, the leader's
`start` and `end`, and `lines` with each line's `text`, `x`, `y`.
Multiply by `viewport.scale` for image pixels.

## Output

`<out>/figures/` holds the PNGs, `manifest.json` and `spec.json`, the spec as given with its
`placement` and `color` fields only where you wrote them, so the
run can be repeated with `run_capture.py <out>/figures/spec.json --out <out>`. Repeating covers the
pictures and not the site: steps that change data may not work twice, so see "Test data" in
SKILL.md. A run replaces only the figures listed in the existing `manifest.json`, plus that file
and `spec.json`. Other files stay. A new figure whose name is taken by something this tool did not
create is refused, as is a directory named `manifest.json` or `spec.json`. This is checked before
the browser starts and again before replacing anything, so nothing changes.
Without a readable manifest no figure counts as this tool's. If replacing fails midway, the earlier
output is restored.

A failed run leaves earlier figures untouched and saves what the page looked like at
`<out>/failures/<slug>.png` (`login.png` for the login), naming that path in the error. Open it:
it usually explains the failure. `failures/` is cleared by the next run and may never be
published.
