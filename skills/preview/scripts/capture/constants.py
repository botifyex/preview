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
FRAMED_KINDS = frozenset({"box", "removed", "ellipse", "highlight", "spotlight"})
LINE_PARTS: dict[str, tuple[tuple[str, str], ...]] = {
    "arrow": (("arrow tail", "tail"), ("arrow tip", "tip")),
    "underline": (("underline start", "start"), ("underline end", "end")),
    "connector": (("connector start", "start"), ("connector end", "end")),
    "callout": (("leader start", "start"), ("leader end", "end")),
}
ELLIPSE_REACH = 2**0.5
HIGHLIGHT_OPACITY = 0.25
SPOTLIGHT_OPACITY = 0.6
CALLOUT_WIDTH = 280
CALLOUT_NARROWEST = 80
CALLOUT_GAP = 28
CALLOUT_PADDING = (12, 10)
CALLOUT_LINE = 20
CALLOUT_SIDES = ("left", "right", "above", "below")
CONNECTOR_MINIMUM = 16
CONNECTOR_HEADS = ("none", "end", "both")
SINGLE_KIND_FIELDS = {"side": "callout", "width": "callout", "heads": "connector"}
KIND_PLACEMENTS = {
    "arrow": ARROW_PLACEMENTS,
    "connector": ARROW_PLACEMENTS,
    "callout": PLACEMENTS - {"inside"},
}
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
    "callout": frozenset({"anchor", "text"}),
    "ellipse": frozenset({"anchor"}),
    "underline": frozenset({"anchor"}),
    "highlight": frozenset({"anchor"}),
    "spotlight": frozenset({"anchor"}),
    "connector": frozenset({"anchor", "from"}),
}
LOCATOR_KEYS = frozenset({"selector", "role", "text"})
