# preview

[![CI](https://github.com/botifyex/preview/actions/workflows/ci.yaml/badge.svg)](https://github.com/botifyex/preview/actions/workflows/ci.yaml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](https://github.com/botifyex/preview/blob/master/LICENSE)

A Claude Code skill that opens your running app, walks its pages and writes a plain-language guide
to what changed in a release or beta, with numbered, annotated screenshots.

## Quick start

You need [Claude Code](https://claude.com/claude-code), [uv](https://docs.astral.sh/uv/) and git.

Install the plugin and the browser:

```bash
claude plugin marketplace add botifyex/preview
claude plugin install preview@preview
uv run --no-project --with playwright==1.64.1 playwright install chromium
```

Start your app, then in Claude Code, inside your project:

```text
/preview:preview access
/preview:preview release
```

The first command saves how to log in as a test user; you only need it once. The second writes
`preview/<version>/RELEASE.md` with its pictures in `figures/`. Use `beta` instead of `release` for the
span of beta versions.

## Examples

Everything below comes from one run against a made-up billing app. Read the
[full sample report](examples/showcase/RELEASE.md) to see what your users would get.

### Step-by-step paths and screen maps

Several screens in one picture, with the state carried from step to step.

<img src="examples/showcase/figures/26-scheme-checkout-path.png" width="800" alt="row with steps_numbers, links: sequence and continuous: true: the cart carries over from step to step">

<code>row</code> with <code>steps_numbers</code>, <code>links: sequence</code> and <code>continuous: true</code>: the cart carries over from step to step

<img src="examples/showcase/figures/28-scheme-screen-map.png" width="800" alt="grid with columns, panel_width and a dark background; links with from_mark, text and a dashed style">

<code>grid</code> with <code>columns</code>, <code>panel_width</code> and a dark <code>background</code>; links with <code>from_mark</code>, <code>text</code> and a dashed style

<img src="examples/showcase/figures/27-scheme-invoice-parts.png" width="688" alt="column of two crops with different crop_padding, each with a title">

<code>column</code> of two <code>crop</code>s with different <code>crop_padding</code>, each with a <code>title</code>

<img src="examples/showcase/figures/29-scheme-hide-overlay.png" width="800" alt="hide: the developer strip shown, then listed in hide">

<code>hide</code>: the developer strip shown, then listed in <code>hide</code>

### Marks

Claude picks the mark that fits what it needs to show.

<table>
<tr>
<td width="33%"><img src="examples/showcase/figures/01-mark-box.png" width="280" alt="box with a number and text"><br><sub><code>box</code> with a number and text</sub></td>
<td width="33%"><img src="examples/showcase/figures/02-mark-arrow-default.png" width="280" alt="arrow, default tail"><br><sub><code>arrow</code>, default tail</sub></td>
<td width="33%"><img src="examples/showcase/figures/03-mark-arrow-offset.png" width="280" alt="arrow with offset"><br><sub><code>arrow</code> with <code>offset</code></sub></td>
</tr>
<tr>
<td width="33%"><img src="examples/showcase/figures/04-mark-arrow-from.png" width="280" alt="arrow with from"><br><sub><code>arrow</code> with <code>from</code></sub></td>
<td width="33%"><img src="examples/showcase/figures/05-mark-badge.png" width="280" alt="badge for steps"><br><sub><code>badge</code> for steps</sub></td>
<td width="33%"><img src="examples/showcase/figures/06-mark-label.png" width="280" alt="label"><br><sub><code>label</code></sub></td>
</tr>
<tr>
<td width="33%"><img src="examples/showcase/figures/07-mark-removed.png" width="280" alt="removed, in its own red"><br><sub><code>removed</code>, in its own red</sub></td>
<td width="33%"><img src="examples/showcase/figures/08-mark-callout.png" width="280" alt="callout with side and width, signed out"><br><sub><code>callout</code> with <code>side</code> and <code>width</code>, signed out</sub></td>
<td width="33%"><img src="examples/showcase/figures/09-mark-ellipse.png" width="280" alt="ellipse"><br><sub><code>ellipse</code></sub></td>
</tr>
<tr>
<td width="33%"><img src="examples/showcase/figures/10-mark-underline.png" width="280" alt="underline"><br><sub><code>underline</code></sub></td>
<td width="33%"><img src="examples/showcase/figures/11-mark-highlight.png" width="280" alt="highlight"><br><sub><code>highlight</code></sub></td>
<td width="33%"><img src="examples/showcase/figures/12-mark-spotlight.png" width="280" alt="spotlight"><br><sub><code>spotlight</code></sub></td>
</tr>
<tr>
<td width="33%"><img src="examples/showcase/figures/13-connector-none.png" width="280" alt="connector, heads: none"><br><sub><code>connector</code>, <code>heads: none</code></sub></td>
<td width="33%"><img src="examples/showcase/figures/14-connector-end.png" width="280" alt="connector, heads: end"><br><sub><code>connector</code>, <code>heads: end</code></sub></td>
<td width="33%"><img src="examples/showcase/figures/15-connector-both.png" width="280" alt="connector, heads: both"><br><sub><code>connector</code>, <code>heads: both</code></sub></td>
</tr>
</table>

### Colours, themes and numbers

Marks use crimson `#E6004C` unless `color` says otherwise; the same field also works for a whole spec.

<table>
<tr>
<td width="33%"><img src="examples/showcase/figures/17-colour-levels.png" width="280" alt="color on the figure (indigo) and one mark (amber); removed keeps its red"><br><sub><code>color</code> on the figure (indigo) and one mark (amber); <code>removed</code> keeps its red</sub></td>
<td width="33%"><img src="examples/showcase/figures/18-dark-theme.png" width="280" alt="theme: dark"><br><sub><code>theme: dark</code></sub></td>
<td width="33%"><img src="examples/showcase/figures/16-number-placements.png" width="280" alt="Every number placement: a deliberate gallery of 10 marks"><br><sub>Every number <code>placement</code>: a deliberate gallery of 10 marks</sub></td>
</tr>
</table>

### Before and after

<table>
<tr>
<td width="33%"><img src="examples/showcase/figures/19-before-after-before.png" width="280" alt="before_url: the old version, marked"><br><sub><code>before_url</code>: the old version, marked</sub></td>
<td width="33%"><img src="examples/showcase/figures/20-before-after.png" width="280" alt="The current version"><br><sub>The current version</sub></td>
</tr>
</table>

### Mobile

<table>
<tr>
<td width="33%"><img src="examples/showcase/figures/21-mobile-touch.png" width="200" alt="390 px wide, has_touch, scale: 2: the touch-only hint"><br><sub>390 px wide, <code>has_touch</code>, <code>scale: 2</code>: the touch-only hint</sub></td>
<td width="33%"><img src="examples/showcase/figures/22-mobile-menu.png" width="200" alt="Steps open the menu"><br><sub>Steps open the menu</sub></td>
</tr>
</table>

### Whole page, window and steps

<table>
<tr>
<td width="33%"><img src="examples/showcase/figures/23-page-whole.png" width="280" alt="full_page: true"><br><sub><code>full_page: true</code></sub></td>
<td width="33%"><img src="examples/showcase/figures/24-page-window.png" width="280" alt="full_page: false"><br><sub><code>full_page: false</code></sub></td>
<td width="33%"><img src="examples/showcase/figures/25-steps-to-hover.png" width="280" alt="Steps: goto, fill, press, wait, click, hover"><br><sub>Steps: goto, fill, press, wait, click, hover</sub></td>
</tr>
</table>

## Installation options

Requirements: uv, git and Chromium for Playwright 1.64.1. Scripts fetch their Python dependencies on first run.
Linux is the only tested platform.

**As a plugin from GitHub**, called `/preview:preview`: the commands in [Quick start](#quick-start). Inside Claude
Code 2.1.275 or later the first two can be one step, which has not been tested:
`/plugin install preview --marketplace botifyex/preview`.

**As a personal skill**, called `/preview`, from a clone of this repository:

```bash
ln -s "$PWD/skills/preview" ~/.claude/skills/preview
```

**As a plugin for one session**, called `/preview:preview`, from a clone:

```bash
claude --plugin-dir "$PWD"
```

## Usage

Called `/preview` as a personal skill and `/preview:preview` as a plugin.

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

The skill never tags, pushes, publishes or changes the project's code, and refuses to create
users or capture when the environment is production or the address is unknown. Test users it
creates are listed in its final message; removing them is up to you. Login sessions are kept in
`~/.cache/preview/state`, outside the target repository, unless `--state-dir` is given.

Status: base version. It has been tested on fixtures and run on one real site; runs on real projects are still limited.

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

## License

[Apache-2.0](LICENSE). Changes are listed in [CHANGELOG.md](CHANGELOG.md). To work on the project, see
[CONTRIBUTING.md](CONTRIBUTING.md); to report a vulnerability, [SECURITY.md](SECURITY.md).
