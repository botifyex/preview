import ssl
import subprocess
from collections.abc import Iterator
from functools import partial
from pathlib import Path

import pytest
from helpers import Capture, serve


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
