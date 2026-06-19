import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

from breadboard.components import register
from breadboard.components.base import _leg_dots
from breadboard.geometry import Geometry
from breadboard.model import Component
from breadboard.style import Style


@register("button")
def _button(axes: plt.Axes, geo: Geometry, component: Component, style: Style) -> None:
    """Draw a pushbutton: a square housing with a round plunger over its legs."""
    holes = [geo.hole(leg) for leg in component.legs]
    xs = [hx for hx, _ in holes]
    ys = [hy for _, hy in holes]
    pad = 0.45
    x0, x1 = min(xs) - pad, max(xs) + pad
    y0, y1 = min(ys) - pad, max(ys) + pad
    axes.add_patch(
        Rectangle(
            (x0, y0), x1 - x0, y1 - y0,
            facecolor="#3a3f44", edgecolor="#1f2326", linewidth=1.0, zorder=4,
        )
    )
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    axes.add_patch(
        Circle((cx, cy), min(x1 - x0, y1 - y0) * 0.28,
               facecolor="#a8302f", edgecolor="#5e1817", linewidth=1.0, zorder=5)
    )
    _leg_dots(axes, style, *holes)
    axes.text(
        cx, y1 + 0.2,
        " ".join(p for p in (component.ref, component.value) if p),
        ha="center", va="bottom", fontsize=8.0, fontweight="bold",
        color=style.color("label.ref"), zorder=6, bbox=style.label_bbox,
    )
