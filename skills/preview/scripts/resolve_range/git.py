import subprocess
from pathlib import Path

from resolve_range.model import RangeFailure

FIELD_SEPARATOR = "\x00"
COMMIT_FORMAT = "%H%x00%s%x00%b%x00"


def run(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    command = ["git", "-C", str(repository), *arguments]
    try:
        return subprocess.run(command, capture_output=True, encoding="utf-8", errors="replace", check=False)
    except OSError as error:
        raise RangeFailure("git is not available: install it or fix PATH") from error


def git(repository: Path, *arguments: str) -> str:
    process = run(repository, *arguments)
    if process.returncode != 0:
        raise RangeFailure(f"git {arguments[0]} failed: {process.stderr.strip()}")
    return process.stdout


def commit_of(repository: Path, reference: str) -> str:
    process = run(repository, "rev-parse", "--verify", "--quiet", f"{reference}^{{commit}}")
    if process.returncode != 0:
        raise RangeFailure(f"'{reference}' is not a commit in {repository}")
    return process.stdout.strip()


def is_tag(repository: Path, name: str) -> bool:
    return run(repository, "rev-parse", "--verify", "--quiet", f"refs/tags/{name}").returncode == 0


def read_commits(repository: Path, start: str, end: str) -> list[dict[str, str]]:
    output = git(repository, "log", "--encoding=UTF-8", f"--format={COMMIT_FORMAT}", f"{start}..{end}")
    fields = output.split(FIELD_SEPARATOR)
    triples = zip(fields[0::3], fields[1::3], fields[2::3], strict=False)
    return [{"hash": commit.strip(), "subject": subject, "body": body.strip()} for commit, subject, body in triples]


def read_files(repository: Path, start: str, end: str) -> list[dict[str, str]]:
    output = git(repository, "diff", "--name-status", "--no-renames", "-z", start, end)
    fields = output.split(FIELD_SEPARATOR)
    return [{"status": status, "path": path} for status, path in zip(fields[0::2], fields[1::2], strict=False)]
