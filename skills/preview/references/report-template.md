# Report template

The report lives at `<out>/RELEASE.md`, next to `figures/`. The structure is fixed and the
language is not: headings follow the language of the project's users, so the validator
reads positions, not words.

```markdown
![Figure 1: the export button](figures/01-export-button.png)
**1.** The export button on the reports page

![Figure 2: the export window](figures/02-export-window.png)
**2.** The window where you choose the format

# What is new in version 2.4

Version 2.4 lets you take your reports with you.

## Main changes

**Reports can now be exported.** Open a report and press the new button
([figure 1](figures/01-export-button.png)). Choose a format in the window that opens
([figure 2](figures/02-export-window.png)): mark 1 is the format, mark 2 starts the download.

## Other changes

- The list of reports opens faster.
- Dates now follow your language setting.
- The old "Print" link is gone: use your browser's print command instead.
```

## Writing

- Say what the person can do and where to find it. "You can export a report", not "added
  an export endpoint".
- Plain words, the user's language, short sentences. No hashes, branch names, file names,
  library names or internal names of things.
- Use the names shown in the interface, exactly as written there.
- Name badge numbers when a figure has several: "mark 2 starts the download".
- The most important change comes first. Say so if something requires action from the user.
- Other changes are one line each. Internal work is left out, or is a single line if it
  matters: "Work behind the scenes to make the site more reliable".
- "New" is a claim about the old version. Before calling anything new, check that it was not
  there at the start of the range: `git show <from>:<path>`, `git grep <words> <from>`, or the
  old version running. A change to something existing is described as a change. If you cannot
  tell, describe what it does without saying "new".
- Be honest. If you could not check something, leave it out or say so. Do not write down what
  only a commit message claims.
- Test users, ports and how the preview was made do not belong here; they go in your message
  to the person running the skill.

## What the validator checks

`check_report.py <dir>` prints `code: message` for every problem and exits 1:

| Code | Problem |
| --- | --- |
| `missing-report` | `<dir>/RELEASE.md` does not exist |
| `images-first` | The first non-empty line is not an image, or a figure is embedded after the title |
| `section-order` | The headings of levels 1 and 2 are not exactly title, main, other |
| `unreferenced-figure` | A figure has no link in the text, or a PNG in `figures/` is not in the report |
| `missing-file` | A figure or a link points at no file, or a link points at a figure not embedded |
| `numbering` | Numbers are not 1, 2, 3 and so on in order, or a name is not `NN-slug.png` |
| `main-without-figure` | The main section links no figure |

A reference is a Markdown link to the figure file, `[figure 1](figures/01-slug.png)`, so it
works in any language and stays clickable. Text between images is allowed, so each figure can
carry a visible caption with its number; headings of level 3 and below are free. Headings
inside code fences do not count. The validator checks structure only: whether the text is
true and plain remains your job.
