import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

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


@register("diode")
def _diode(axes: plt.Axes, geo: Geometry, component: Component, style: Style) -> None:
    """Draw a diode body with a cathode band on the second leg."""
    p1, p2 = geo.hole(component.legs[0]), geo.hole(component.legs[1])
    ux, uy, nx, ny, mx, my, length = _leg_frame(p1, p2)
    body_half = min(0.32 * length, 0.5)
    width = 0.18
    e1, e2 = _draw_leads(axes, p1, p2, ux, uy, body_half, style)
    axes.add_patch(
        Polygon(
            _body_quad(e1, e2, nx, ny, width),
            closed=True,
            facecolor=style.color("diode.body"),
            edgecolor=style.color("diode.body_edge"),
            linewidth=style.dim("diode.body_edge_width"), zorder=4,
        )
    )
    bx, by = e2[0] - ux * 0.14, e2[1] - uy * 0.14
    axes.add_patch(
        Polygon(
            _body_quad(
                (bx - ux * 0.04, by - uy * 0.04),
                (bx + ux * 0.04, by + uy * 0.04),
                nx, ny, width,
            ),
            closed=True, facecolor=style.color("diode.band"),
            edgecolor="none", zorder=4.5,
        )
    )
    _leg_dots(axes, style, p1, p2)
    _part_label(axes, mx, my, nx, ny, component.ref, component.value, style)
