import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "preview" / "scripts"


def run_script(name: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "--quiet", str(SCRIPTS / name), *arguments],
        capture_output=True,
        text=True,
        timeout=300,
    )


class Repository:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.counter = 0
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        self.git("config", "tag.gpgsign", "false")
        self.git("config", "commit.gpgsign", "false")

    def git(self, *arguments: str) -> str:
        process = subprocess.run(
            ["git", "-C", str(self.path), *arguments], capture_output=True, text=True, check=True
        )
        return process.stdout.strip()

    def commit(self, subject: str, body: str = "") -> str:
        self.counter += 1
        (self.path / f"file{self.counter}.txt").write_text(subject)
        self.git("add", ".")
        arguments = ["commit", "-q", "-m", subject]
        if body:
            arguments += ["-m", body]
        self.git(*arguments)
        return self.git("rev-parse", "HEAD")

    def tag(self, name: str, annotated: bool = False) -> None:
        if annotated:
            self.git("tag", "-a", name, "-m", name)
        else:
            self.git("tag", name)

    def tagged(self, *names: str) -> None:
        for name in names:
            self.commit(f"before {name}")
            self.tag(name)


@pytest.fixture
def repository(tmp_path: Path) -> Repository:
    directory = tmp_path / "repository"
    directory.mkdir()
    return Repository(directory)
