---
name: preview
description: Opens a running project, walks its pages and writes a numbered, visually annotated, plain-language guide to what changed in the last release or beta, for ordinary users. Images first, then a title, the main changes referencing the images, then everything else. Also creates the note that explains how to get a test user into the panel.
when_to_use: Only on explicit request. Triggers - "/preview", "preview", "покажи что изменилось в релизе", "превью релиза", "гайд по релизу с картинками", "что нового в бете с картинками". Do not trigger for plain changelog work, version bumps or publishing a release.
argument-hint: "<access|release|beta> [--from <ref>] [--to <ref>] [--note <path>] [--out <dir>]"
disable-model-invocation: true
---

# Preview

Arguments: `$ARGUMENTS`

## Resolve the mode

The first word of the arguments names the mode; an unambiguous prefix is accepted.

| Mode | Use for |
| --- | --- |
| `access` | Create or update the note |
| `release` | The last stable version up to now |
| `beta` | The span of beta versions |

Everything after the mode word is options. Without arguments, list these modes and stop. An
unknown mode: name the modes that exist and stop; don't guess.

Defaults: `--note .preview/access.md`, `--out preview/<label>/`,
where `<label>` comes from the range script. `--from` and `--to` override the range.

## Hard limits

- Never tag, push, publish a release, or change the project's code. The only files
  written in the repository are the note (in `access` mode) and the output directory.
  Sessions go to `~/.cache/preview/state`, outside it, unless `--state-dir` says
  otherwise. Nothing is committed.
- Never create users or capture when `environment` is production or `base_url` is
  unknown. Say so and stop.
- The note holds no real secrets: only environment variable names or throwaway values.
- Commands in the note come from the repository. Show them to the user and get an
  answer before running them the first time in this session.
- Never claim anything from a commit message that you did not see on the page. What
  you could not see is either left out or said plainly to be unverified.
- Screenshots show test data only. If real personal data or a secret is visible,
  discard the image.

## Scripts

Run from the target repository. Each script installs its own dependencies through
`uv run`. All three exit 0 on success and 1 with a specific message on stderr.

Claude Code replaces `${CLAUDE_SKILL_DIR}` below when it loads this file, for a personal skill
and a plugin alike. It is not an environment variable in the shell. If you see it unreplaced
here (for example this file was read directly), use the directory that holds this `SKILL.md`.

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/run_resolve_range.py" <release|beta> [--repo <dir>] [--from <ref>] [--to <ref>]
uv run "${CLAUDE_SKILL_DIR}/scripts/run_capture.py" <spec.json> --out <dir> [--state-dir <dir>] [--ignore-https-errors] [--fresh-login] [--timeout <ms>]
uv run "${CLAUDE_SKILL_DIR}/scripts/check_report.py" <dir>
```

- `run_resolve_range.py` prints JSON with `from`, `to`, `label`, `notes`, `commits`, `files`:
  [references/range.md](references/range.md).
- `run_capture.py` writes `<dir>/figures/NN-slug.png` and `manifest.json`, all or nothing:
  [references/capture-spec.md](references/capture-spec.md).
- `check_report.py` checks `<dir>/RELEASE.md` against `<dir>/figures/` and prints
  `code: message` per problem: [references/report-template.md](references/report-template.md).

## Test data

Steps that create or change data are not repeatable, and "all or nothing" covers files, not
the site: a failed or repeated capture leaves its changes behind.

- Use a fresh user with a new `{unique}` for each run, so each starts from a known empty state.
  After a failure that changed data, start over with another fresh user.
- Seed only in the way the note documents (`seed`, or through the interface as steps). Never
  write to the database directly and never reset shared data.
- Keep data creation out of what repeats: seed first, then let figures only open pages when you can.

## Mode `access`

Follow [references/access-note.md](references/access-note.md): derive the note from
reading the project, show its commands to the user, prove it with a real login, and
only then save it. If a note exists, update it the same way.

## Modes `release` and `beta`

### 1. Read the note

Read the note at `--note`. If it is missing, offer `access` mode and stop until it is
done. Check `environment` and `base_url` against the hard limits.

### 2. Resolve the range

Run `run_resolve_range.py` with the mode and any `--from` and `--to`. Tell the user the
`from` and `to` it chose and every entry of `notes`. On an error, pass on the message;
do not guess a range. If `commits` is empty, say there is nothing to preview and stop.

### 3. Read commits and diff

Read every subject and body, then the diff of files that look user-facing
(`git diff <from> <to> -- <path>`). A commit message says what someone meant to do;
the diff and the page say what happened. For each thing you think is new, check the old code
at `from` (`git show <from>:<path>`, `git grep <words> <from>`). A feature that was already there
and only changed is a change, not an addition: testers have wrongly reported existing behaviour
as new from a diff that merely touched it.

### 4. Separate user-visible from internal

Sort each change into: main (a user would notice and care), other (small fixes, minor
behaviour, things worth knowing), internal (refactors, tests, build, dependencies).
Internal changes are left out or get one line.

If nothing is user-visible, tell the user and stop; do not write a report: the
validator requires at least one figure.

### 5. Plan the figures

List for the user: figure number, page, state to reach, what is marked. Plan one idea
per image, following [references/annotation-design.md](references/annotation-design.md).
The plan contains only what the changes support, and nothing is drawn on a guess: every
mark must land on an element that the run itself finds.

### 6. Reach the stack

Check whether `base_url` answers. If not, start the stack with the note's command,
after showing it. Do not change the project's configuration to make it start. Local
certificates need `--ignore-https-errors`.

### 7. Create the test user

Follow the note, replacing its `{unique}` placeholder with a fresh value such as a
timestamp. Pass the password through an environment variable when you can. Remember
each user you create for the final report.

### 8. Capture

Write the spec into the scratchpad or a temporary directory, never into the project's
tracked files, and run `run_capture.py`. A failure means the page differs from your plan:
open the picture named in the error and find out why. A selector miss is information, possibly that the
change is not there. Use `hide` for development overlays and `login: false` for signed-out figures.

For removed things, follow "Removed things" in the annotation reference.

### 9. Look at each image

Open every PNG with Read. Fix the spec and capture again when:

- a mark is on the wrong thing, covers what it should show, or is unreadable;
- the page shows an error, a spinner, an empty state or a login form by accident;
- real personal data or a secret is visible;
- the image does not show the claim you plan to make.

Treat warnings on stderr (too many marks) the same way.

### 10. Write the report

Write `<out>/RELEASE.md` from [references/report-template.md](references/report-template.md),
in the language of the project's users (the language of its interface). Plain words: what
the person can now do and where. No hashes, branch names, file names, class names or
jargon. Every claim about the main changes points at a figure.

Say honestly what you could not verify: a removal with no old version to compare with is
described in words, and a change you could not see is either left out or marked as such.

### 11. Validate

Run `check_report.py <out>`. Fix the report until it passes; never rename or delete a
figure just to silence it without checking the text still matches the image.

### 12. Report to the user

Tell the user: the path of `RELEASE.md`, the range, the number of figures, what was left
unverified, every test user and piece of test data you created, anything you started and left
running. Say how to remove the users using the note's `remove_user`. If the project has no way,
say plainly that they remain, propose a removal, and do not run it. Do not delete test users or
stop the stack unless asked. `RELEASE.md` itself stays free of this: it is for ordinary users.

## References

Load on demand:

- [references/access-note.md](references/access-note.md): note format and `access` procedure
- [references/range.md](references/range.md): range rules and JSON output
- [references/capture-spec.md](references/capture-spec.md): capture spec and manifest
- [references/annotation-design.md](references/annotation-design.md): how to mark images
- [references/report-template.md](references/report-template.md): report template and validator rules
