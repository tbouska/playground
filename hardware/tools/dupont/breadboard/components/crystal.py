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


@register("crystal")
def draw_crystal(axes: plt.Axes, geo: Geometry, component: Component, style: Style) -> None:
    p1, p2 = geo.hole(component.legs[0]), geo.hole(component.legs[1])
    ux, uy, nx, ny, mx, my, length = _leg_frame(p1, p2)
    body_half = min(0.35 * length, 0.55)
    width = 0.25
    e1, e2 = _draw_leads(axes, p1, p2, ux, uy, body_half, style)
    axes.add_patch(
        Polygon(
            _body_quad(e1, e2, nx, ny, width),
            closed=True,
            facecolor=style.color("crystal.body"),
            edgecolor=style.color("crystal.body_edge"),
            linewidth=style.dim("crystal.body_edge_width"),
            zorder=4,
        )
    )
    for ex, ey in (e1, e2):
        axes.add_patch(
            Circle(
                (ex, ey),
                width,
                facecolor=style.color("crystal.body"),
                edgecolor=style.color("crystal.body_edge"),
                linewidth=style.dim("crystal.body_edge_width"),
                zorder=4,
            )
        )
    _leg_dots(axes, style, p1, p2)
    _part_label(axes, mx, my, nx, ny, component.ref, component.value, style)
