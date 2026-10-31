# Range rules

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/run_resolve_range.py" <release|beta> [--repo <dir>] [--from <ref>] [--to <ref>]
```

## Which tags count

Version tags are ordered by version, never by date. Other tags are ignored.

| Spelling | Examples | Stage |
| --- | --- | --- |
| Stable | `v1.2.0`, `1.2.0`, `v1.2` | stable |
| Alpha | `v1.2.0-alpha.1`, `1.2.0a1` | alpha |
| Beta | `v1.2.0-beta.1`, `1.2.0b1` | beta |
| Candidate | `v1.2.0-rc.1`, `1.2.0rc1` | rc |

Order: alpha, then beta, then rc, then stable. Number compares as a number, so `beta.10`
follows `beta.2`. Build metadata (`+abc`) is accepted and does not affect the order.

Ignored as not versions: `nightly`, `v1`, `pkg-1.2.0`, `v1.2.0-foo`, `1.2.0.dev1`,
`1.2.0.post1`. Only tags reachable from the end of the range count.

**The beta channel is beta plus rc.** An rc goes out to the same testers as a beta, so
it is a boundary of the beta span. Alpha is not: it is recognised and never used as a
boundary in either mode.

## Mode `release`

| Situation | `from` | `to` |
| --- | --- | --- |
| HEAD is past the latest stable | latest stable | `HEAD` |
| HEAD is the latest stable | previous stable | that tag |
| HEAD is the only stable tag | error, suggests `--from` | |
| No stable tag | error, suggests `--from` | |

## Mode `beta`

| Situation | `from` | `to` |
| --- | --- | --- |
| HEAD is past the latest beta, no newer stable | latest beta | `HEAD` |
| HEAD is the latest beta | newest beta or stable below it | that tag |
| A stable is newer than the latest beta, HEAD is past it | that stable, with a note | `HEAD` |
| A stable is newer than the latest beta, HEAD is it | latest beta, with a note | that stable |
| No beta or rc tag | error, suggests `--from` | |

A stable release newer than the last beta moves the start: everything before it is
already released, so beta testers should be told only about what came after. A stable
between two betas works the same way when HEAD is at the later beta: its span starts at
that stable, not at the previous beta. The script adds an entry to `notes` for the two
stable cases of the table; pass every note on to the user.

## Overrides

`--to <ref>` replaces HEAD: the rules above apply as if HEAD were that ref. `--from <ref>`
skips the search, so it works with no tags at all. Two tags on one commit never produce
an empty range: the previous version must be a different commit.

## Output

```json
{
  "mode": "release",
  "from": "v1.1.0",
  "to": "HEAD",
  "from_commit": "<full hash>",
  "to_commit": "<full hash>",
  "label": "v1.1.0--HEAD",
  "notes": ["<why an unusual start was chosen>"],
  "commits": [{ "hash": "<full hash>", "subject": "Add export", "body": "<message body>" }],
  "files": [{ "status": "M", "path": "src/export.ts" }]
}
```

`to` is the tag when `--from` is used and the end is tagged. `label` is safe as a directory
name and is the default output directory's last part: the tag when the range ends at a
version, otherwise `<from>--<to>`. Commits are newest first and merges are included. File
status is git's `A`, `M`, `D` or `T`; a rename appears as `D` plus `A`.
