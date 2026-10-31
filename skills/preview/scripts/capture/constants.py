import re

PLAYWRIGHT_VERSION = "1.64.1"
PRODUCTION_NAMES = frozenset({"production", "prod", "live"})
THEMES = frozenset({"light", "dark"})
DEFAULT_VIEWPORT = {"width": 1280, "height": 800, "scale": 1}
SLUG_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
FIGURE_PATTERN = re.compile(r"\d{2,}-.+\.png")
MANIFEST_NAME = "manifest.json"
SPEC_NAME = "spec.json"
FAILURES_NAME = "failures"
IDENTITY_LENGTH = 12
BADGE_MARGIN = 16
BADGE_RADIUS = 14
BADGE_REACH = 20
BADGE_INSET = 18
TAIL_PLACEMENTS = frozenset({"corner", "top-left"})
OUTSIDE_PLACEMENTS = frozenset({"left", "right", "above", "below"})
ARROW_PLACEMENTS = TAIL_PLACEMENTS | OUTSIDE_PLACEMENTS
PLACEMENTS = ARROW_PLACEMENTS | frozenset({"top-right", "bottom-left", "bottom-right", "inside"})
DEFAULT_PLACEMENT = "corner"
COLOR_PATTERN = re.compile(r"#[0-9A-Fa-f]{6}")
DEFAULT_COLOR = "#E6004C"
KIND_COLORS = {"removed": "#C81E1E"}
MATCH_KINDS = frozenset({"exact", "substring", "regex"})
FLAG_FIELDS = ("has_touch", "reduced_motion")
BOX_PADDING = 4
EDGE_MARGIN = 2
ARROW_REACH = (80, 60)
MARK_ADVICE = 5
IDLE_LIMIT = 3000
STABLE_POLL = 100
NUMBER_LIMIT = 1_000_000_000
BACKUP_PREFIX = ".capture-backup-"
INCOMING_NAME = "incoming"
FRAMED_KINDS = frozenset({"box", "removed"})
STEP_FIELDS: dict[str, frozenset[str]] = {
    "goto": frozenset({"url"}),
    "fill": frozenset({"target"}),
    "click": frozenset({"target"}),
    "hover": frozenset({"target"}),
    "press": frozenset({"key"}),
    "wait": frozenset(),
}
ANNOTATION_FIELDS: dict[str, frozenset[str]] = {
    "box": frozenset({"anchor"}),
    "arrow": frozenset({"anchor"}),
    "badge": frozenset({"anchor", "number"}),
    "label": frozenset({"anchor", "text"}),
    "removed": frozenset({"anchor", "offset"}),
}
LOCATOR_KEYS = frozenset({"selector", "role", "text"})
