# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-10-31

### Added

- `/preview release` and `/preview beta` open a running project, walk its pages and write
  `preview/<version-or-range>/RELEASE.md` with numbered, annotated images in `figures/`: a plain-language
  guide for ordinary users, with the images first, then a title, the main changes referencing the images,
  and everything else. `--from`, `--to`, `--note` and `--out` override the defaults.
- `/preview access` creates or updates `.preview/access.md`, the note that says how to get a test user
  into the panel. It is confirmed by a real login before saving and never holds real secrets.
- `release` covers the latest stable version up to now and `beta` the span of beta versions, with beta and
  rc counting as beta and alpha not. Semantic and PEP 440 tags are ordered by version number, not by date.
- `run_resolve_range.py` prints the chosen range as JSON and works without the skill.
- `run_capture.py` walks the pages in a JSON spec and draws marks on the real elements, with steps
  (`goto`, `fill`, `press`, `click`, `hover`, `wait`), a saved login, `theme`, `viewport`, `has_touch`,
  `scale`, `full_page` and `hide`. Its options are `--out`, `--state-dir`, `--ignore-https-errors`,
  `--fresh-login` and `--timeout`.
- Eleven kinds of marks: `box`, `arrow`, `badge`, `label`, `removed`, `callout`, `ellipse`, `underline`,
  `highlight`, `spotlight` and `connector`.
- `color` on a mark, a figure or the whole spec sets the colour of marks; the default is `#E6004C`, and
  `removed` keeps its own red unless the mark itself sets one.
- `before_url` captures the old version of a page as its own numbered figure before the current one.
- Schemes: a figure with `panels` combines several captures into one image as a `row`, `column` or `grid`,
  with `links` between panels and marks, `crop`, `title` and `steps_numbers`. `continuous: true` carries the
  state of one panel over to the next.
- `check_report.py` checks a report's order, references, numbering and files.
- `examples/showcase`, a sample report on a fictional billing app that shows every kind of mark and scheme
  and can be rebuilt with `uv run examples/showcase/build.py`.
- Installation as a personal skill by a symbolic link, or as a Claude Code plugin from `--plugin-dir` or
  from the marketplace in this repository.

### Security

- The skill and `run_capture.py` both refuse to create users or capture when the environment is production
  or the address is unknown.
- Login sessions stay outside the target repository, in `~/.cache/preview/state` unless `--state-dir` is
  given, with files readable only by their owner. A literal password in a password field of the spec is
  an error, so it cannot reach the saved `figures/spec.json`.
- `run_capture.py` publishes all or nothing and replaces only the files its own manifest lists, refusing
  to overwrite anything else.

[Unreleased]: https://github.com/botifyex/preview/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/botifyex/preview/releases/tag/v0.1.0
