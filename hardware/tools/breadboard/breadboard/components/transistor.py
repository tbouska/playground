import math

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

from breadboard.components import register
from breadboard.components.base import _leg_dots
from breadboard.geometry import Geometry
from breadboard.model import Component
from breadboard.style import LABEL_BBOX


def _dome_outline(
    cx: float, cy: float, radius: float, flat_y: float
) -> list[tuple[float, float]]:
    """Circle outline clipped to a flat bottom at ``flat_y`` (a TO-92 shape)."""
    steps = 48
    return [
        (
            cx + radius * math.cos(2 * math.pi * i / steps),
            max(cy + radius * math.sin(2 * math.pi * i / steps), flat_y),
        )
        for i in range(steps + 1)
    ]


@register("transistor")
def _transistor(axes: plt.Axes, geo: Geometry, component: Component) -> None:
    """Draw a TO-92 transistor: a D-shaped body over three leg holes."""
    holes = [geo.hole(leg) for leg in component.legs]
    cx = sum(hx for hx, _ in holes) / len(holes)
    base_y = max(hy for _, hy in holes)
    radius = 0.6
    body_cy = base_y + 0.85
    flat_y = body_cy - radius * 0.5
    for hx, hy in holes:
        axes.plot([hx, hx], [hy, flat_y], color="#555", linewidth=1.4, zorder=3)
    axes.add_patch(
        Polygon(
            _dome_outline(cx, body_cy, radius, flat_y),
            closed=True, facecolor="#23282d", edgecolor="#0f1316",
            linewidth=1.0, zorder=4,
        )
    )
    _leg_dots(axes, *holes)
    axes.text(
        cx, body_cy + radius * 0.55 + 0.2,
        " ".join(p for p in (component.ref, component.value) if p),
        ha="center", va="bottom", fontsize=8.0, fontweight="bold",
        color="#1f1f1f", zorder=6, bbox=LABEL_BBOX,
    )
