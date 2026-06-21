import matplotlib.pyplot as plt
from matplotlib.patches import Circle

from breadboard.components import register
from breadboard.components.base import (
    _draw_leads,
    _leg_dots,
    _leg_frame,
    _part_label,
)
from breadboard.geometry import Geometry
from breadboard.model import Component
from breadboard.style import Style


@register("buzzer")
def draw_buzzer(axes: plt.Axes, geo: Geometry, component: Component, style: Style) -> None:
    p1, p2 = geo.hole(component.legs[0]), geo.hole(component.legs[1])
    ux, uy, nx, ny, mx, my, length = _leg_frame(p1, p2)
    body_half = min(0.34 * length, 0.5)
    radius = 0.38
    _draw_leads(axes, p1, p2, ux, uy, body_half, style)
    # Body: round can
    axes.add_patch(
        Circle(
            (mx, my),
            radius,
            facecolor=style.color("buzzer.body"),
            edgecolor=style.color("buzzer.body_edge"),
            linewidth=style.dim("buzzer.body_edge_width"),
            zorder=4,
        )
    )
    # Sound hole (small circle at centre)
    axes.add_patch(
        Circle(
            (mx, my),
            radius * 0.3,
            facecolor=style.color("buzzer.hole"),
            edgecolor="none",
            zorder=5,
        )
    )
    # + mark: placed between centre and p1 (legs[0] side)
    plus_x = (mx + p1[0]) / 2
    plus_y = (my + p1[1]) / 2
    axes.text(
        plus_x, plus_y, "+",
        ha="center", va="center",
        fontsize=7, fontweight="bold",
        color=style.color("buzzer.plus"),
        zorder=6,
    )
    _leg_dots(axes, style, p1, p2)
    _part_label(axes, mx, my, nx, ny, component.ref, component.value, style)
