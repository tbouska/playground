"""Compose the board, wires, and registered component drawers into a figure.

`render` is the orchestration entry point: it builds the geometry, draws the
board substrate and wires, dispatches each component to its registered drawer
via the component registry, and writes the SVG + PNG output.
"""

import logging
from pathlib import Path

import matplotlib.pyplot as plt

from breadboard.board import _draw_board
from breadboard.components import get_drawer
from breadboard.geometry import Geometry
from breadboard.model import Layout
from breadboard.style import Style, load_style
from breadboard.wires import _draw_wires, _wire_channels

_LOG = logging.getLogger("breadboard")


def render(layout: Layout, out_stem: Path, style: Style | None = None) -> None:
    """Render a layout to ``<stem>.svg`` and ``<stem>.png``.

    :param layout: The layout to render.
    :type layout: Layout
    :param out_stem: The output path without extension.
    :type out_stem: Path
    :returns: None. The function writes the two image files to disk.
    :rtype: None
    """
    if style is None:
        style = load_style()
    geo = Geometry(layout.columns)
    width = max(8.0, layout.columns * 0.42)
    figure, axes = plt.subplots(figsize=(width, 6.5))
    _draw_board(axes, geo, style)

    channels = _wire_channels(geo, layout.components)
    _draw_wires(axes, geo, layout.components, channels, style)
    for component in layout.components:
        if component.kind == "wire":
            continue  # wires are drawn by _draw_wires, not the component registry
        drawer = get_drawer(component.kind)
        if drawer is None:
            _LOG.warning("unknown component kind %r; skipping", component.kind)
            continue
        drawer(axes, geo, component, style)

    axes.set_title(layout.title, fontsize=12, color=style.color("title.color"))
    axes.set_aspect("equal")
    axes.axis("off")
    axes.autoscale_view()
    figure.tight_layout()
    figure.savefig(out_stem.with_suffix(".svg"))
    figure.savefig(out_stem.with_suffix(".png"), dpi=style.dim("render.dpi"))
    plt.close(figure)
