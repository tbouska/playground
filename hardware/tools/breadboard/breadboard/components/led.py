import math

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon

from breadboard.components import register
from breadboard.components.base import _leg_dots, _tint
from breadboard.geometry import Geometry
from breadboard.model import Component
from breadboard.style import Style


def _led_lens(axes: plt.Axes, cx: float, cy: float, radius: float, fill: str) -> None:
    """Draw a round LED lens with a flat cathode edge and a highlight."""
    flat_x = cx + radius * 0.72
    steps = 48
    outline = [
        (
            min(cx + radius * math.cos(2 * math.pi * i / steps), flat_x),
            cy + radius * math.sin(2 * math.pi * i / steps),
        )
        for i in range(steps + 1)
    ]
    axes.add_patch(
        Polygon(
            outline,
            closed=True,
            facecolor=fill,
            edgecolor="#8d6a62",
            linewidth=1.2,
            alpha=0.95,
            zorder=4,
        )
    )
    axes.add_patch(
        Circle(
            (cx - radius * 0.3, cy + radius * 0.33),
            radius * 0.26,
            facecolor="white",
            edgecolor="none",
            alpha=0.5,
            zorder=4.5,
        )
    )


@register("led", "led-rgb")
def _led(axes: plt.Axes, geo: Geometry, component: Component, style: Style) -> None:
    """Draw an RGB LED (named legs) or a single LED (two ordered legs)."""
    if component.named_legs:
        leads = [
            (style.channel_colors.get(name, style.color("led.fallback")), geo.hole(hole))
            for name, hole in component.named_legs.items()
        ]
        lens_fill = "#f6d9d2"
        caption = f"{component.ref} RGB ({'CC' if component.common == 'cathode' else 'CA'})"
    else:
        leads = [
            (style.color("led.fallback"), geo.hole(component.legs[0])),
            (style.color("led.fallback"), geo.hole(component.legs[1])),
        ]
        lens_fill = _tint(component.color)
        caption = component.ref
    holes = [point for _, point in leads]
    cx = sum(hx for hx, _ in holes) / len(holes)
    cy = max(hy for _, hy in holes) + 0.95
    radius = 0.5
    for color, (hx, hy) in leads:
        axes.plot([hx, cx], [hy, cy], color=color, linewidth=1.6, zorder=3)
    _leg_dots(axes, style, *holes)
    _led_lens(axes, cx, cy, radius, lens_fill)
    axes.text(
        cx, cy + radius + 0.28, caption,
        ha="center", va="bottom", fontsize=8.0, fontweight="bold",
        color=style.color("label.ref"), zorder=6, bbox=style.label_bbox,
    )
