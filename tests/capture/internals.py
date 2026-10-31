import importlib
import sys
from pathlib import Path
from types import ModuleType

SCRIPTS = Path(__file__).resolve().parent.parent.parent / "skills" / "preview" / "scripts"


def internal(name: str) -> ModuleType:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    module = importlib.import_module(f"capture.{name}")
    assert Path(module.__file__ or "").is_relative_to(SCRIPTS)
    return module
