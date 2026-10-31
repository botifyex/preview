import json
import shutil
from pathlib import Path

from capture.constants import FIGURE_PATTERN, MANIFEST_NAME, SPEC_NAME
from capture.model import Spec


def publish(staging: Path, figures: Path, entries: list[Spec], spec: Spec) -> None:
    figures.mkdir(parents=True, exist_ok=True)
    for old in figures.iterdir():
        if FIGURE_PATTERN.fullmatch(old.name) or old.name in (MANIFEST_NAME, SPEC_NAME):
            old.unlink()
    for new in staging.iterdir():
        shutil.move(str(new), figures / new.name)
    manifest = {"environment": spec["environment"], "base_url": spec["base_url"], "figures": entries}
    (figures / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    (figures / SPEC_NAME).write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n")
