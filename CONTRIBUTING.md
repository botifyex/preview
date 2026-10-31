# Contributing

## Development

```sh
uv sync
uv run playwright install chromium     # once; add --with-deps on a machine without its system libraries
uv run pytest tests -n auto
uv run ruff check .
uv run ruff format --check .
uv run basedpyright
uv lock --check
```

Tests use real temporary git repositories, a local HTTP server and real Chromium, and the scripts run
through their own `uv run` as they do for a user. Linux is the only tested platform.

Versions and rules live in `pyproject.toml`. It holds tool configuration and pinned development
dependencies only: nothing is built or installed, and the scripts keep their own PEP 723 headers.

Reasons behind the choices and the backlog are in Russian: [docs/decisions.md](docs/decisions.md),
[docs/backlog.md](docs/backlog.md).

Every push to `master` and every pull request runs CI: `lint` runs ruff, basedpyright and `uv lock --check`;
`test` runs the whole suite on Python 3.12, 3.13 and 3.14, including the rebuild of the showcase.

A change to the project's own documents only (`README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`,
`LICENSE`, `NOTICE`, `docs/`) runs the `Docs` workflow instead: the tests that check them, without a browser.
Files under `skills/` always run everything, because capture tests execute the examples in the references.

## Showcase

```sh
uv run examples/showcase/build.py
```

This rewrites `examples/showcase/figures/` from `examples/showcase/spec.json` and the site beside it, then
checks `examples/showcase/RELEASE.md`. Commit the result together with the change that caused it, after
looking at the images: a test rebuilds the figures and compares the manifest with the committed one.

The build shows Chromium only the fonts in `examples/showcase/fonts`, where Liberation Sans stands in for
Arial, so positions in the manifest do not depend on the fonts of the machine. Text in the site must stay
within that font: draw pictograms as inline SVG.

## Releases

Releases follow [Semantic Versioning](https://semver.org/) and are recorded in
[CHANGELOG.md](CHANGELOG.md).

1. Add entries under `## [Unreleased]` in `CHANGELOG.md` together with the changes.
2. Bump the version with a clean working tree: `uvx bump-my-version bump patch|minor|major`.
   It updates `pyproject.toml`, `uv.lock`, `.claude-plugin/plugin.json` and `CHANGELOG.md`, commits and
   creates the `v<version>` tag.
3. Push with `git push --follow-tags`, then publish a GitHub release from that tag.

Nothing is uploaded anywhere: users install from the repository.
