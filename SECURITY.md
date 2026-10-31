# Security policy

## Reporting a vulnerability

Please do not open a public issue for security problems. Report them privately through
[GitHub security advisories](https://github.com/botifyex/preview/security/advisories/new)
with a description, the affected version and, if possible, steps to reproduce.

You will get an answer within a week. Once a fix is released, the advisory is published with
credit to the reporter unless you prefer otherwise.

## Supported versions

Only the latest release receives security fixes.

## Scope

Of particular interest are ways to:

- reach a production environment or an unknown address despite the refusal;
- leak a login session file or a secret into the output, the report, the manifest or the saved
  `figures/spec.json`;
- make publishing delete or overwrite files the skill does not own;
- read or write outside the output directory through a path in a manifest or a spec.
