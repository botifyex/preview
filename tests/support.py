import subprocess
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "preview" / "scripts"


def run_script(name: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "--quiet", str(SCRIPTS / name), *arguments],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
