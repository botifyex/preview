# The access note

Default location: `.preview/access.md` in the target repository. It tells the
skill how to reach the panel with a test user. It is safe to commit, because it never
holds real secrets. Machine-read fields go in YAML frontmatter; explanations in prose.

## Format

```markdown
---
base_url: https://localhost:8443
environment: local
start: just up
stop: just down
certificates: self-signed
create_user:
  kind: command
  run: just create-user --email preview-{unique}@example.com --password "$PREVIEW_PASSWORD"
remove_user: just delete-user --email preview-{unique}@example.com
password_env: PREVIEW_PASSWORD
login:
  name: preview-user
  steps:
    - { action: goto, url: /login }
    - { action: fill, target: { role: textbox, name: Email }, value: "preview-{unique}@example.com" }
    - { action: fill, target: { role: textbox, name: Password }, value_env: PREVIEW_PASSWORD }
    - { action: click, target: { role: button, name: Sign in } }
  expect: { role: heading, name: Dashboard }
pages:
  - { path: /dashboard, purpose: main panel }
  - { path: /settings, purpose: account settings }
never:
  - "Do not send real email: the mail service in this stack is a sink, keep it so."
  - Do not touch the billing pages.
---

# How to reach the panel

Anything the fields do not capture: why the steps are what they are, what a fresh
database looks like, which role the test user needs and how to grant it.
```

## Fields

| Field | Required | Meaning |
| --- | --- | --- |
| `base_url` | yes | Address of the running non-production stack |
| `environment` | yes | `local`, `dev`, `staging`, `test`. `production`, `prod` or `live` means refuse |
| `start`, `stop` | no | Commands from the repository that run the stack |
| `certificates` | no | `self-signed` means pass `--ignore-https-errors` |
| `create_user.kind` | yes | `command`, `api` or `ui` |
| `create_user.run` | for `command` | Command, with the `{unique}` placeholder |
| `create_user.request` | for `api` | See "`create_user` by API" |
| `create_user.steps` | for `ui` | Capture-style steps, with `{unique}` |
| `remove_user` | no | How to remove the test user, for the final report. See "Removing test users" |
| `password_env` | no | Name of the variable holding a throwaway password. Generate one if unset |
| `login` | yes | `name`, `steps` and `expect`, in the shape of the capture spec's `login` |
| `seed` | no | The documented way to create test data for a user, with `{unique}` |
| `pages` | yes | Pages worth walking, with their purpose |
| `never` | yes | Things never to do here. May be an empty list, stated deliberately |

`{unique}` is replaced by a fresh value on each run, so repeated runs do not collide.
Quote any YAML string containing `: `, or it parses as a mapping. Use `example.com` for test
addresses: validators often refuse reserved domains such as `.test`.

## `create_user` by API

```yaml
create_user:
  kind: api
  request:
    method: POST
    path: /api/users
    headers: { X-Requested-With: preview }
    json: { email: "preview-{unique}@example.com", password: "{password}" }
    status: 201
```

`method`, `path`, `json` and `status` are required; `path` is relative to `base_url`, and
`status` is the answer that means success. Any other answer is a failure: show it and stop.

`{password}` stands for the value of the variable named by `password_env`. It is replaced
only when the request is sent and is never written into the note or a file. Send the body on
standard input, so the password stays out of the process list:

```bash
curl --fail-with-body --silent --show-error --request POST "$BASE_URL/api/users" \
  --header "Content-Type: application/json" --data @- <<< "$BODY"
```

Add `--insecure` only when the note says `certificates: self-signed` and `base_url` is on
this machine (`localhost`, `127.0.0.1`, a local test domain). Never use it for another host;
stop and ask instead. The browser's equivalent is `--ignore-https-errors`.

## Removing test users

`remove_user` is optional, because many projects have no way to do it. When it is missing:
do not invent a removal. No direct database deletes, no admin calls, nothing unproven. Say
plainly in the final message which users are left behind and where, propose a removal the
user could run or approve, and leave it unrun. When `remove_user` exists, still only report
it: test users are removed on request.

## Procedure of `access` mode

1. Read how the project runs: README, agent instructions, `justfile`, `Makefile`,
   `package.json` scripts, compose files, seed scripts, registration routes, auth tests.
   Read `.env.example`, not `.env`.
2. Decide `environment` and `base_url`. If you cannot tell they are non-production, ask.
   If the answer is production or stays unknown, write no user-creating steps and stop.
3. Draft the note in memory. Every command must exist in the repository; quote its
   source when you show it.
4. Show the user the note and the commands you are about to run. Wait for an answer.
5. Prove it: start the stack if needed, create a user with a fresh `{unique}`, and log
   in with `capture.py`, using a spec with the note's `login`, one figure on the first
   page after login, and a temporary `--out`. Then open that image with Read and confirm
   it is really the panel.
6. Only after that real login, save the note. If it fails, fix the draft or report what
   blocks it; never save a note that was not proven.
7. Tell the user the test user you created and how to remove it, or that the project has no
   way to do so (see "Removing test users").

Updating an existing note follows the same steps; change only what is wrong or missing.
A note that contains something that looks like a real secret: stop and tell the user.
