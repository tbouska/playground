import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon

from breadboard.components import register
from breadboard.components.base import (
    _body_quad,
    _draw_leads,
    _leg_dots,
    _leg_frame,
    _part_label,
)
from breadboard.geometry import Geometry
from breadboard.model import Component
from breadboard.style import Style


@register("capacitor")
def _capacitor(axes: plt.Axes, geo: Geometry, component: Component, style: Style) -> None:
    """Draw a ceramic (disc) or electrolytic (striped cylinder) capacitor."""
    p1, p2 = geo.hole(component.legs[0]), geo.hole(component.legs[1])
    ux, uy, nx, ny, mx, my, length = _leg_frame(p1, p2)
    polar = component.common.strip().lower() in (
        "anode", "polar", "polarized", "electrolytic", "+",
    )
    if polar:
        body_half = min(0.34 * length, 0.5)
        width = 0.34
        e1, e2 = _draw_leads(axes, p1, p2, ux, uy, body_half, style)
        axes.add_patch(
            Polygon(
                _body_quad(e1, e2, nx, ny, width),
                closed=True,
                facecolor=style.color("capacitor.polar_body"),
                edgecolor=style.color("capacitor.polar_body_edge"),
                linewidth=style.dim("capacitor.polar_body_edge_width"), zorder=4,
            )
        )
        # Light stripe marks the negative (second) leg of an electrolytic.
        sx, sy = e2[0] - ux * 0.13, e2[1] - uy * 0.13
        axes.add_patch(
            Polygon(
                _body_quad(
                    (sx - ux * 0.05, sy - uy * 0.05),
                    (sx + ux * 0.05, sy + uy * 0.05),
                    nx, ny, width,
                ),
                closed=True, facecolor=style.color("capacitor.polar_stripe"),
                edgecolor="none", zorder=4.5,
            )
        )
    else:
        body_half = min(0.28 * length, 0.36)
        e1, e2 = _draw_leads(axes, p1, p2, ux, uy, body_half, style)
        axes.add_patch(
            Circle(
                ((e1[0] + e2[0]) / 2, (e1[1] + e2[1]) / 2),
                0.34,
                facecolor=style.color("capacitor.ceramic_body"),
                edgecolor=style.color("capacitor.ceramic_body_edge"),
                linewidth=style.dim("capacitor.ceramic_body_edge_width"), zorder=4,
            )
        )
    _leg_dots(axes, style, p1, p2)
    _part_label(axes, mx, my, nx, ny, component.ref, component.value, style)
