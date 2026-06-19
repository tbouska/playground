import copy
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

HOLE_RADIUS = 0.18
RENDER_DPI = 200
RAIL_PLUS_COLOR = "#c0392b"
RAIL_MINUS_COLOR = "#2c5fb3"
BOARD_COLOR = "#efeae0"
BOARD_EDGE = "#b7b0a0"
SHADOW_COLOR = "#8a8478"
HIGHLIGHT_COLOR = "#fbf8f1"
HOLE_FILL = "#dcd6ca"
HOLE_EDGE = "#a59e8c"
HOLE_SHADOW = "#c8c1af"
HOLE_HILITE = "#ebe6da"
# Connection-dot radius, shared by wires and every component lead/pin.
DOT_RADIUS = 0.13
# IEC resistor colour code, indexed by digit (0-9).
RESISTOR_DIGIT_COLORS = (
    "#1a1a1a", "#7a4a1e", "#c0392b", "#e67e22", "#f1c40f",
    "#27ae60", "#2c5fb3", "#8e44ad", "#7f8c8d", "#f2f2f2",
)
# Sub-unity multiplier bands and the 5-band tolerance band (brown = 1%).
RESISTOR_MULTIPLIER_EXTRA = {-1: "#cda434", -2: "#bfc1c2"}  # gold x0.1, silver x0.01
RESISTOR_TOLERANCE = "#7a4a1e"
GAP_COLOR = "#d2cabb"
GAP_SHADOW = "#a79f8d"
BODY_COLOR = "#e8e2d4"
CHANNEL_COLORS: dict[str, str] = {"R": "#c0392b", "G": "#27ae60", "B": "#2c5fb3"}
HOP_RADIUS = 0.22
# Board-coloured halo behind text so wires routed beneath cannot scratch it.
LABEL_BBOX: dict[str, Any] = {
    "boxstyle": "round,pad=0.18",
    "facecolor": BOARD_COLOR,
    "edgecolor": "none",
    "alpha": 0.82,
}

_DEFAULT_PATH = Path(__file__).resolve().parent / "assets" / "style.yaml"
_log = logging.getLogger("breadboard")


@dataclass(frozen=True)
class Style:
    """Resolved palette + scalar dimensions, addressed by dotted key."""

    data: dict[str, Any]

    def color(self, key: str) -> str:
        """Hex colour at a dotted key, e.g. ``color("hole.shadow")``."""
        return self._get(key)

    def dim(self, key: str) -> float:
        """Scalar dimension at a dotted key, e.g. ``dim("dot.radius")``."""
        return self._get(key)

    def _get(self, key: str) -> Any:
        node: Any = self.data
        for part in key.split("."):
            node = node[part]
        return node

    @property
    def resistor_digit_colors(self) -> tuple[str, ...]:
        return tuple(self._get("resistor.digit_colors"))

    @property
    def resistor_multiplier_extra(self) -> dict[int, str]:
        return {int(k): v for k, v in self._get("resistor.multiplier_extra").items()}

    @property
    def channel_colors(self) -> dict[str, str]:
        return dict(self._get("channel"))

    @property
    def label_bbox(self) -> dict[str, Any]:
        """Label halo: board-coloured rounded box, so labels sit on the board."""
        return {
            "boxstyle": "round,pad=0.18",
            "facecolor": self.color("board.fill"),
            "edgecolor": "none",
            "alpha": 0.82,
        }


def _deep_merge(base: dict, override: dict, path: str = "") -> None:
    """Merge override into base in-place; unknown keys are warned and skipped."""
    for key, value in override.items():
        dotted = f"{path}.{key}" if path else key
        if key not in base:
            _log.warning("unknown style key %r", dotted)
            continue
        if isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value, dotted)
        else:
            base[key] = value


def load_style(path: str | Path | None = None, inline: dict | None = None) -> Style:
    """Resolve the default stylesheet, deep-merged with optional overrides.

    Precedence (low -> high): bundled defaults < ``path`` file < ``inline`` dict.
    User keys override defaults; missing keys fall back to defaults; keys not
    present in the default schema log a ``logging.warning`` and are ignored
    (never crash, never injected).
    """
    with _DEFAULT_PATH.open() as f:
        defaults = yaml.safe_load(f)

    resolved = copy.deepcopy(defaults)

    if path is not None:
        with Path(path).open() as f:
            file_override = yaml.safe_load(f)
        if file_override:
            _deep_merge(resolved, file_override)

    if inline is not None:
        _deep_merge(resolved, inline)

    return Style(data=resolved)
