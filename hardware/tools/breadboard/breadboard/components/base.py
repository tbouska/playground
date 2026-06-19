import math

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from matplotlib.patches import Circle

from breadboard.style import Style


def _leg_frame(
    p1: tuple[float, float], p2: tuple[float, float]
) -> tuple[float, float, float, float, float, float, float]:
    """Return axis unit ``(ux, uy)``, normal ``(nx, ny)``, midpoint and length."""
    (x1, y1), (x2, y2) = p1, p2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    return ux, uy, -uy, ux, (x1 + x2) / 2, (y1 + y2) / 2, length


def _draw_leads(
    axes: plt.Axes,
    p1: tuple[float, float],
    p2: tuple[float, float],
    ux: float,
    uy: float,
    body_half: float,
    style: Style,
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Draw the two lead wires up to the body; return the body end points."""
    mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    e1 = (mx - ux * body_half, my - uy * body_half)
    e2 = (mx + ux * body_half, my + uy * body_half)
    axes.plot([p1[0], e1[0]], [p1[1], e1[1]], color=style.color("lead.color"), linewidth=style.dim("lead.width"), zorder=3)
    axes.plot([p2[0], e2[0]], [p2[1], e2[1]], color=style.color("lead.color"), linewidth=style.dim("lead.width"), zorder=3)
    return e1, e2


def _leg_dots(axes: plt.Axes, style: Style, *holes: tuple[float, float]) -> None:
    """Mark each connection hole with a dot the same weight as wire ends."""
    for hx, hy in holes:
        axes.add_patch(
            Circle((hx, hy), style.dim("dot.radius"), facecolor=style.color("dot.fill"), edgecolor="none", zorder=5)
        )


def _part_label(
    axes: plt.Axes, x: float, y: float, nx: float, ny: float, ref: str, value: str, style: Style
) -> None:
    """Print a part's reference (heavier) above its value (lighter)."""
    if value:
        axes.text(
            x + nx * 0.5, y + ny * 0.5, value,
            ha="center", va="center", fontsize=6.8, color=style.color("label.value"),
            zorder=6, bbox=style.label_bbox,
        )
    if ref:
        axes.text(
            x + nx * 0.92, y + ny * 0.92, ref,
            ha="center", va="center", fontsize=8.5, fontweight="bold",
            color=style.color("label.ref"), zorder=6, bbox=style.label_bbox,
        )


def _body_quad(
    e1: tuple[float, float],
    e2: tuple[float, float],
    nx: float,
    ny: float,
    half_width: float,
) -> list[tuple[float, float]]:
    """Rectangle corners for a body running from ``e1`` to ``e2``."""
    return [
        (e1[0] + nx * half_width, e1[1] + ny * half_width),
        (e2[0] + nx * half_width, e2[1] + ny * half_width),
        (e2[0] - nx * half_width, e2[1] - ny * half_width),
        (e1[0] - nx * half_width, e1[1] - ny * half_width),
    ]


def _tint(color: str) -> tuple[float, float, float]:
    """Lighten a colour (name or hex) halfway to white for an LED lens."""
    r, g, b = to_rgb(color)
    return tuple(c + (1.0 - c) * 0.5 for c in (r, g, b))
