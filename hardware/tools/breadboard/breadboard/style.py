import copy
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

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
            "boxstyle": f"round,pad={self.dim('label.halo_pad')}",
            "facecolor": self.color("board.fill"),
            "edgecolor": "none",
            "alpha": 0.82,
        }


def _deep_merge(base: dict, override: dict, path: str = "") -> None:
    """Merge override into base in-place; unknown or wrong-shaped keys are warned and skipped."""
    for key, value in override.items():
        dotted = f"{path}.{key}" if path else key
        if key not in base:
            _log.warning("unknown style key %r", dotted)
            continue
        base_is_dict = isinstance(base[key], dict)
        if base_is_dict and isinstance(value, dict):
            _deep_merge(base[key], value, dotted)
        elif base_is_dict != isinstance(value, dict):
            _log.warning("style key %r has wrong shape; keeping default", dotted)
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
