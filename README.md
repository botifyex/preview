# preview

A Claude Code skill that opens a running project, walks its pages and writes a numbered,
visually annotated, plain-language guide to what changed in a release or beta, for ordinary
users. The report goes: images, title, main changes referencing the images, everything else.

Status: base version. It has been tested on fixtures, not yet on a real project.

## Install

Nothing is installed by the repository itself. Needs [uv](https://docs.astral.sh/uv/), git,
and Chromium for Playwright 1.64.1. Scripts fetch their Python dependencies on first run.

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

Reasons behind the choices, in Russian: [docs/decisions.md](docs/decisions.md).
