# preview

[![CI](https://github.com/botifyex/preview/actions/workflows/ci.yaml/badge.svg)](https://github.com/botifyex/preview/actions/workflows/ci.yaml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](https://github.com/botifyex/preview/blob/master/LICENSE)

A Claude Code skill that opens a running project, walks its pages and writes a numbered,
visually annotated, plain-language guide to what changed in a release or beta, for ordinary
users. The report goes: images, title, main changes referencing the images, everything else.

Status: base version. It has been tested on fixtures and run on one real site; runs on real projects are still limited.

## What it looks like

Every picture below comes from one spec run against a fictional billing app; all its data is made up. The full
sample report is [examples/showcase/RELEASE.md](examples/showcase/RELEASE.md). To rebuild it:

```bash
uv run examples/showcase/build.py
```

### Marks

<table>
<tr>
<td width="33%"><img src="examples/showcase/figures/01-mark-box.png" width="280" alt="<code>box</code> with a number and text"><br><sub><code>box</code> with a number and text</sub></td>
<td width="33%"><img src="examples/showcase/figures/02-mark-arrow-default.png" width="280" alt="<code>arrow</code>, default tail"><br><sub><code>arrow</code>, default tail</sub></td>
<td width="33%"><img src="examples/showcase/figures/03-mark-arrow-offset.png" width="280" alt="<code>arrow</code> with <code>offset</code>"><br><sub><code>arrow</code> with <code>offset</code></sub></td>
</tr>
<tr>
<td width="33%"><img src="examples/showcase/figures/04-mark-arrow-from.png" width="280" alt="<code>arrow</code> with <code>from</code>"><br><sub><code>arrow</code> with <code>from</code></sub></td>
<td width="33%"><img src="examples/showcase/figures/05-mark-badge.png" width="280" alt="<code>badge</code> for steps"><br><sub><code>badge</code> for steps</sub></td>
<td width="33%"><img src="examples/showcase/figures/06-mark-label.png" width="280" alt="<code>label</code>"><br><sub><code>label</code></sub></td>
</tr>
<tr>
<td width="33%"><img src="examples/showcase/figures/07-mark-removed.png" width="280" alt="<code>removed</code>, in its own red"><br><sub><code>removed</code>, in its own red</sub></td>
<td width="33%"><img src="examples/showcase/figures/08-mark-callout.png" width="280" alt="<code>callout</code> with <code>side</code> and <code>width</code>, signed out"><br><sub><code>callout</code> with <code>side</code> and <code>width</code>, signed out</sub></td>
<td width="33%"><img src="examples/showcase/figures/09-mark-ellipse.png" width="280" alt="<code>ellipse</code>"><br><sub><code>ellipse</code></sub></td>
</tr>
<tr>
<td width="33%"><img src="examples/showcase/figures/10-mark-underline.png" width="280" alt="<code>underline</code>"><br><sub><code>underline</code></sub></td>
<td width="33%"><img src="examples/showcase/figures/11-mark-highlight.png" width="280" alt="<code>highlight</code>"><br><sub><code>highlight</code></sub></td>
<td width="33%"><img src="examples/showcase/figures/12-mark-spotlight.png" width="280" alt="<code>spotlight</code>"><br><sub><code>spotlight</code></sub></td>
</tr>
<tr>
<td width="33%"><img src="examples/showcase/figures/13-connector-none.png" width="280" alt="<code>connector</code>, <code>heads: none</code>"><br><sub><code>connector</code>, <code>heads: none</code></sub></td>
<td width="33%"><img src="examples/showcase/figures/14-connector-end.png" width="280" alt="<code>connector</code>, <code>heads: end</code>"><br><sub><code>connector</code>, <code>heads: end</code></sub></td>
<td width="33%"><img src="examples/showcase/figures/15-connector-both.png" width="280" alt="<code>connector</code>, <code>heads: both</code>"><br><sub><code>connector</code>, <code>heads: both</code></sub></td>
</tr>
</table>

### Colour, themes and numbers

Marks use the default crimson `#E6004C` unless `color` says otherwise; the same field also works for a whole spec.

<table>
<tr>
<td width="33%"><img src="examples/showcase/figures/17-colour-levels.png" width="280" alt="<code>color</code> on the figure (indigo) and one mark (amber); <code>removed</code> keeps its red"><br><sub><code>color</code> on the figure (indigo) and one mark (amber); <code>removed</code> keeps its red</sub></td>
<td width="33%"><img src="examples/showcase/figures/18-dark-theme.png" width="280" alt="<code>theme: dark</code>"><br><sub><code>theme: dark</code></sub></td>
<td width="33%"><img src="examples/showcase/figures/16-number-placements.png" width="280" alt="Every number <code>placement</code>: a deliberate gallery of 10 marks"><br><sub>Every number <code>placement</code>: a deliberate gallery of 10 marks</sub></td>
</tr>
</table>

### Before and after

<table>
<tr>
<td width="33%"><img src="examples/showcase/figures/19-before-after-before.png" width="280" alt="<code>before_url</code>: the old version, marked"><br><sub><code>before_url</code>: the old version, marked</sub></td>
<td width="33%"><img src="examples/showcase/figures/20-before-after.png" width="280" alt="The current version"><br><sub>The current version</sub></td>
</tr>
</table>

### Mobile

<table>
<tr>
<td width="33%"><img src="examples/showcase/figures/21-mobile-touch.png" width="200" alt="390 px wide, <code>has_touch</code>, <code>scale: 2</code>: the touch-only hint"><br><sub>390 px wide, <code>has_touch</code>, <code>scale: 2</code>: the touch-only hint</sub></td>
<td width="33%"><img src="examples/showcase/figures/22-mobile-menu.png" width="200" alt="Steps open the menu"><br><sub>Steps open the menu</sub></td>
</tr>
</table>

### Whole page, window and steps

<table>
<tr>
<td width="33%"><img src="examples/showcase/figures/23-page-whole.png" width="280" alt="<code>full_page: true</code>"><br><sub><code>full_page: true</code></sub></td>
<td width="33%"><img src="examples/showcase/figures/24-page-window.png" width="280" alt="<code>full_page: false</code>"><br><sub><code>full_page: false</code></sub></td>
<td width="33%"><img src="examples/showcase/figures/25-steps-to-hover.png" width="280" alt="Steps: goto, fill, press, wait, click, hover"><br><sub>Steps: goto, fill, press, wait, click, hover</sub></td>
</tr>
</table>

### Schemes

One image from several captures.

<img src="examples/showcase/figures/26-scheme-checkout-path.png" width="800" alt="<code>row</code> with <code>steps_numbers</code>, <code>links: sequence</code> and <code>continuous: true</code>: the cart carries over from step to step">

<code>row</code> with <code>steps_numbers</code>, <code>links: sequence</code> and <code>continuous: true</code>: the cart carries over from step to step

<img src="examples/showcase/figures/28-scheme-screen-map.png" width="800" alt="<code>grid</code> with <code>columns</code>, <code>panel_width</code> and a dark <code>background</code>; links with <code>from_mark</code>, <code>text</code> and a dashed style">

<code>grid</code> with <code>columns</code>, <code>panel_width</code> and a dark <code>background</code>; links with <code>from_mark</code>, <code>text</code> and a dashed style

<img src="examples/showcase/figures/27-scheme-invoice-parts.png" width="688" alt="<code>column</code> of two <code>crop</code>s with different <code>crop_padding</code>, each with a <code>title</code>">

<code>column</code> of two <code>crop</code>s with different <code>crop_padding</code>, each with a <code>title</code>

<img src="examples/showcase/figures/29-scheme-hide-overlay.png" width="800" alt="<code>hide</code>: the developer strip shown, then listed in <code>hide</code>">

<code>hide</code>: the developer strip shown, then listed in <code>hide</code>

## Install

Nothing is installed by the repository itself. Needs [uv](https://docs.astral.sh/uv/), git,
and Chromium for Playwright 1.64.1. Scripts fetch their Python dependencies on first run. Linux is the only
tested platform.

From GitHub, as a plugin, called `/preview:preview`:

```bash
claude plugin marketplace add botifyex/preview
claude plugin install preview@preview
```

Or in one step inside Claude Code 2.1.275 or later: `/plugin install preview --marketplace botifyex/preview`.
These two commands were checked against a local copy of this repository, which they installed and enabled; the
same commands against GitHub can only be checked once the repository is published, and the one-step form has
not been run.

From this directory, as a personal skill, called `/preview`:

```bash
ln -s "$PWD/skills/preview" ~/.claude/skills/preview
```

Or as a plugin for one session, called `/preview:preview`:

```bash
claude --plugin-dir "$PWD"
```

If Chromium is missing:

```bash
uv run --no-project --with playwright==1.64.1 playwright install chromium
```

## Use

```text
/preview access
/preview release [--from <ref>] [--to <ref>] [--note <path>] [--out <dir>]
/preview beta    [--from <ref>] [--to <ref>] [--note <path>] [--out <dir>]
```

- `access` creates or updates the note, `.preview/access.md` by default, which says how
  to get a test user into the panel. It is confirmed by a real login before saving and never
  holds real secrets: see [the format](skills/preview/references/access-note.md).
- `release` covers the latest stable version up to now, `beta` the span of beta versions (beta
  and rc count, alpha does not): see [the rules](skills/preview/references/range.md).
- The result is `preview/<version-or-range>/RELEASE.md` with `figures/` beside it.

Marks come in eleven kinds (`box`, `arrow`, `badge`, `label`, `removed`, `callout`, `ellipse`, `underline`,
`highlight`, `spotlight`, `connector`). A scheme combines several captures into one image as a `row`, `column` or
`grid`: see [the capture spec](skills/preview/references/capture-spec.md).
Worked example: [examples/showcase](examples/showcase/RELEASE.md) is generated from this repository.

The skill never tags, pushes, publishes or changes the project's code, and refuses to create
users or capture when the environment is production or the address is unknown. Test users it
creates are listed in its final message; removing them is up to you. Login sessions are kept in
`~/.cache/preview/state`, outside the target repository, unless `--state-dir` is given.

## Scripts

Usable on their own. Each exits 0 on success and 1 with a specific message on stderr.

```bash
uv run skills/preview/scripts/run_resolve_range.py <release|beta> [--repo <dir>] [--from <ref>] [--to <ref>]
uv run skills/preview/scripts/run_capture.py <spec.json> --out <dir> [--state-dir <dir>] [--ignore-https-errors] [--fresh-login] [--timeout <ms>]
uv run skills/preview/scripts/check_report.py <dir>
```

- [`run_resolve_range.py`](skills/preview/references/range.md) prints the range as JSON.
- [`run_capture.py`](skills/preview/references/capture-spec.md) walks the pages in a JSON spec
  and draws marks on the real elements. It fails when a locator does not match, rather than
  drawing at a guessed spot.
- [`check_report.py`](skills/preview/references/report-template.md) checks the report's order,
  references, numbering and files.

## Tests

```bash
uv run pytest tests -n auto
```

Tests use real temporary git repositories, a local HTTP server, and real Chromium.

## Checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run basedpyright
```

Versions and rules live in `pyproject.toml`. It holds tool configuration and pinned development
dependencies only: nothing is built or installed, and the scripts keep their own PEP 723 headers.

Reasons behind the choices and the backlog are in Russian: [docs/decisions.md](docs/decisions.md),
[docs/backlog.md](docs/backlog.md).

## License

[Apache-2.0](LICENSE). Changes are listed in [CHANGELOG.md](CHANGELOG.md); see also
[CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).
