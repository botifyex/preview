# Capture spec

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/capture.py" <spec.json> --out <dir> [--state-dir <dir>] [--ignore-https-errors] [--fresh-login] [--timeout <ms>]
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `--out` | required | Writes `<dir>/figures/` |
| `--state-dir` | `$XDG_CACHE_HOME/preview/state`, else `~/.cache/preview/state` | Saved login sessions, outside the target repository. A `*` `.gitignore` is written inside, files are mode 600 |
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
is refused. `locale`, `hide` and `login` are optional. `figures` is required. Relative URLs
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
`false`, every anchor must lie inside the viewport or the run fails. `has_touch: true` and
`reduced_motion: true` set those browser features. `login: false` keeps a figure signed out in
a run that has a `login`; if every figure does so, no login happens.

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

`box`, `arrow`, `removed` also accept `number` and `text`.

`placement` chooses where a mark's number sits. It can be set on the annotation, the figure or
the top level of the spec; the nearest wins, and with none it is `corner`. An invalid value fails
and names its level. It has no effect on a mark without a `number`.

| `placement` | Number sits | Applies to |
| --- | --- | --- |
| `corner`, `top-left` | On the top left corner; on the tail for an arrow | all |
| `top-right`, `bottom-left`, `bottom-right` | On that corner | all but arrows |
| `inside` | Fully inside, at the top left. A shape under 36 px in width or height fails | all but arrows |
| `left`, `right`, `above`, `below` | Fully outside, 20 px from that side. Off the page fails | all; for an arrow, beside its target |

The shape is the drawn rectangle: the element plus 4 px, or the `removed` place. `badge` and `label`
draw no rectangle and use the same one. An arrow has no inside or corners of its own, so naming one
of those on the annotation fails; inherited from the figure or spec, it falls back to the tail.
Corner placements are moved back onto the page at its edges.

Failures rather than guesses:
an arrow starting inside its target or outside the page, a `removed` place outside the page,
a label wider than the page, anchors that keep moving.

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
host, so an old version on another address must log in through `before_steps`.

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

`role` is `current` or `before`. `element` is the measured box in CSS pixels of the document,
`rectangle` the drawn one, `badge` the centre of the number, `null` without a number. Arrows add `tail` and `tip`.
Multiply by `viewport.scale` for image pixels.

## Output

`<out>/figures/` holds the PNGs, `manifest.json` and `spec.json`, the spec as given with its
`placement` fields only where you wrote them, so the
run can be repeated with `capture.py <out>/figures/spec.json --out <out>`. Repeating covers the
pictures and not the site: steps that change data may not work twice, so see "Test data" in
SKILL.md. A run replaces earlier figures.

A failed run leaves earlier figures untouched and saves what the page looked like at
`<out>/failures/<slug>.png` (`login.png` for the login), naming that path in the error. Open it:
it usually explains the failure. `failures/` is cleared by the next run and may never be
published.
