import ssl
import subprocess
from collections.abc import Iterator
from functools import partial
from pathlib import Path

import pytest
from capture_support import Capture, serve


class Repository:
    def __init__(self, path: Path) -> None:
        self.path: Path = path
        self.counter: int = 0
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        self.git("config", "tag.gpgsign", "false")
        self.git("config", "commit.gpgsign", "false")

    def git(self, *arguments: str) -> str:
        process = subprocess.run(["git", "-C", str(self.path), *arguments], capture_output=True, text=True, check=True)
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


@pytest.fixture(scope="module")
def site() -> Iterator[str]:
    yield from serve()


@pytest.fixture(scope="module")
def secure_site(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    directory = tmp_path_factory.mktemp("certificate")
    certificate, key = directory / "certificate.pem", directory / "key.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-subj",
            "/CN=127.0.0.1",
            "-keyout",
            str(key),
            "-out",
            str(certificate),
            "-days",
            "1",
        ],
        check=True,
        capture_output=True,
    )
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certificate, key)
    yield from serve(partial(context.wrap_socket, server_side=True))


@pytest.fixture
def capture(tmp_path: Path, site: str) -> Capture:
    return Capture(tmp_path, site)
