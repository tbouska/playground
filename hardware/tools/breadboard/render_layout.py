"""Render a breadboard hole-placement layout from a declarative YAML file.

This module reads a hole-placement description (components addressed to specific
breadboard holes such as ``F12`` or rail holes such as ``B-28``) and draws a
realistic breadboard with power rails, the A-J banks, the center gap and
numbered columns, then places each component on its addressed holes. Output is
SVG and PNG, matching the schematic renderer so both views build the same way.

Imports:
    math -- compute lead and body geometry for two-leg components.
    re -- parse hole addresses into row and column parts.
    sys -- read the optional YAML path from the command line.
    dataclasses -- model the parsed layout as frozen value objects.
    pathlib -- resolve input and output file paths.
    typing -- supply :class:`Any` for the untyped parsed YAML mapping.
    matplotlib -- force the headless ``Agg`` backend, then draw with
        :mod:`matplotlib.pyplot` and :mod:`matplotlib.patches`.
    yaml -- parse the description with :func:`yaml.safe_load`.
"""

# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "matplotlib>=3.8",
#     "pyyaml>=6.0",
# ]
# ///

import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from breadboard.geometry import GRID_ADDRESS, LINE_ORDER, RAIL_ADDRESS, Geometry
from breadboard.model import Layout, Pin
from breadboard.parse import load_layout, _component_from_dict
from breadboard.style import (
    BOARD_COLOR,
    BOARD_EDGE,
    GAP_COLOR,
    GAP_SHADOW,
    HIGHLIGHT_COLOR,
    HOLE_EDGE,
    HOLE_FILL,
    HOLE_HILITE,
    HOLE_RADIUS,
    HOLE_SHADOW,
    HOP_RADIUS,
    RAIL_MINUS_COLOR,
    RAIL_PLUS_COLOR,
    RENDER_DPI,
    SHADOW_COLOR,
)
from breadboard.board import _draw_board
from breadboard.wires import (
    _block_rects,
    _hits_block,
    _wire_channels,
    _wire_points,
    _hop_polyline,
    _draw_wire,
    _draw_wires,
)
import logging
from breadboard.components import get_drawer

_LOG = logging.getLogger("breadboard")




class Geometry:
    """Map hole addresses to drawing coordinates for a board width.

    :ivar columns: The number of numbered columns.
    :vartype columns: int
    :ivar line_y: The y coordinate of each named line.
    :vartype line_y: dict[str, float]
    """

    def __init__(self, columns: int) -> None:
        """Build the geometry for a board with the given column count.

        :param columns: The number of numbered columns.
        :type columns: int
        """
        self.columns = columns
        self.line_y = {
            key: -float(index) for index, key in enumerate(LINE_ORDER) if key
        }

    def hole(self, address: str) -> tuple[float, float]:
        """Resolve a hole address to an ``(x, y)`` coordinate.

        :param address: A hole address such as ``"F12"`` or ``"B-28"``.
        :type address: str
        :returns: The coordinate of the hole center.
        :rtype: tuple[float, float]
        :raises ValueError: If the address does not match a known hole.
        """
        rail = RAIL_ADDRESS.match(address)
        if rail:
            return float(rail.group(2)), self.line_y[rail.group(1)]
        grid = GRID_ADDRESS.match(address)
        if grid:
            return float(grid.group(2)), self.line_y[grid.group(1)]
        raise ValueError(f"invalid hole address: {address!r}")


def render(layout: Layout, out_stem: Path) -> None:
    """Render a layout to ``<stem>.svg`` and ``<stem>.png``.

    :param layout: The layout to render.
    :type layout: Layout
    :param out_stem: The output path without extension.
    :type out_stem: Path
    :returns: None. The function writes the two image files to disk.
    :rtype: None
    """
    geo = Geometry(layout.columns)
    width = max(8.0, layout.columns * 0.42)
    figure, axes = plt.subplots(figsize=(width, 6.5))
    _draw_board(axes, geo)

    channels = _wire_channels(geo, layout.components)
    _draw_wires(axes, geo, layout.components, channels)
    for component in layout.components:
        drawer = get_drawer(component.kind)
        if drawer is None:
            _LOG.warning("unknown component kind %r; skipping", component.kind)
            continue
        drawer(axes, geo, component)

    axes.set_title(layout.title, fontsize=12, color="#222")
    axes.set_aspect("equal")
    axes.axis("off")
    axes.autoscale_view()
    figure.tight_layout()
    figure.savefig(out_stem.with_suffix(".svg"))
    figure.savefig(out_stem.with_suffix(".png"), dpi=RENDER_DPI)
    plt.close(figure)


def main() -> None:
    """Parse the YAML path from the command line and render the layout.

    :returns: None. The function writes the rendered image files to disk.
    :rtype: None
    """
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("layout.yaml")
    render(load_layout(source), source.with_suffix(""))


if __name__ == "__main__":
    main()
