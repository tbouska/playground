import math

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

from breadboard.components import register
from breadboard.components.base import _leg_dots
from breadboard.geometry import Geometry
from breadboard.model import Component
from breadboard.style import Style


@register("potentiometer")
def draw_potentiometer(axes: plt.Axes, geo: Geometry, component: Component, style: Style) -> None:
    """Draw a potentiometer: rectangular body with a round knob and a wiper tick."""
    holes = [geo.hole(leg) for leg in component.legs]
    cx = sum(hx for hx, _ in holes) / len(holes)
    cy = sum(hy for _, hy in holes) / len(holes)

    body_w, body_h = 1.2, 1.2
    body_x = cx - body_w / 2
    body_y = cy - body_h / 2

    # Leads from each hole up to the body bottom edge
    lead_top_y = body_y
    for hx, hy in holes:
        axes.plot(
            [hx, hx], [hy, lead_top_y],
            color=style.color("lead.color"), linewidth=style.dim("lead.width"), zorder=3,
        )

    # Body rectangle
    axes.add_patch(
        Rectangle(
            (body_x, body_y), body_w, body_h,
            facecolor=style.color("potentiometer.body"),
            edgecolor=style.color("potentiometer.body_edge"),
            linewidth=style.dim("potentiometer.body_edge_width"),
            zorder=4,
        )
    )

    # Knob circle centred on body
    knob_radius = 0.35
    axes.add_patch(
        Circle(
            (cx, cy), knob_radius,
            facecolor=style.color("potentiometer.knob"),
            edgecolor=style.color("potentiometer.knob_edge"),
            linewidth=style.dim("potentiometer.knob_edge_width"),
            zorder=5,
        )
    )

    # Wiper tick: short line from knob centre toward legs[1]
    wx, wy = geo.hole(component.legs[1])
    dx, dy = wx - cx, wy - cy
    dist = math.hypot(dx, dy) or 1.0
    tick_len = knob_radius * 0.8
    axes.plot(
        [cx, cx + (dx / dist) * tick_len],
        [cy, cy + (dy / dist) * tick_len],
        color=style.color("potentiometer.wiper"),
        linewidth=style.dim("lead.width"),
        zorder=6,
    )

    _leg_dots(axes, style, *holes)

    axes.text(
        cx, body_y + body_h + 0.2,
        " ".join(p for p in (component.ref, component.value) if p),
        ha="center", va="bottom", fontsize=8.0, fontweight="bold",
        color=style.color("label.ref"), zorder=6, bbox=style.label_bbox,
    )
