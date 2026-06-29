import math

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

_N_LOOPS = 4


def _coil_polyline(
    e1: tuple[float, float],
    e2: tuple[float, float],
    nx: float,
    ny: float,
    half_width: float,
    n_loops: int,
    steps_per_half: int = 16,
) -> tuple[list[float], list[float]]:
    n_half = n_loops * 2
    total_steps = n_half * steps_per_half
    (x1, y1), (x2, y2) = e1, e2
    xs: list[float] = []
    ys: list[float] = []
    for i in range(total_steps + 1):
        t = i / total_steps
        cx = x1 + t * (x2 - x1)
        cy = y1 + t * (y2 - y1)
        half_idx = i / steps_per_half
        side = 1 if int(half_idx) % 2 == 0 else -1
        bump = side * half_width * math.sin(math.pi * (i % steps_per_half) / steps_per_half)
        xs.append(cx + nx * bump)
        ys.append(cy + ny * bump)
    return xs, ys


@register("inductor")
def draw_inductor(axes: plt.Axes, geo: Geometry, component: Component, style: Style) -> None:
    p1, p2 = geo.hole(component.legs[0]), geo.hole(component.legs[1])
    ux, uy, nx, ny, mx, my, length = _leg_frame(p1, p2)
    body_half = min(0.40 * length, 0.65)
    half_width = 0.22
    e1, e2 = _draw_leads(axes, p1, p2, ux, uy, body_half, style)
    axes.add_patch(
        Polygon(
            _body_quad(e1, e2, nx, ny, half_width * 1.2),
            closed=True,
            facecolor=style.color("inductor.body"),
            edgecolor=style.color("inductor.body_edge"),
            linewidth=style.dim("inductor.body_edge_width"),
            zorder=4,
        )
    )
    xs, ys = _coil_polyline(e1, e2, nx, ny, half_width, _N_LOOPS)
    axes.plot(
        xs, ys,
        color=style.color("inductor.coil"),
        linewidth=style.dim("inductor.coil_width"),
        zorder=5,
    )
    _leg_dots(axes, style, p1, p2)
    _part_label(axes, mx, my, nx, ny, component.ref, component.value, style)
