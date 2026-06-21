import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

from breadboard.components import register
from breadboard.geometry import Geometry
from breadboard.model import Component
from breadboard.style import Style


@register("module", "power")
def _block(axes: plt.Axes, geo: Geometry, component: Component, style: Style, section: str = "block") -> None:
    """Draw a module or power block spanning its pin rows across the banks."""
    first, last = component.span
    if component.pins:
        pin_ys = [geo.hole(pin.hole)[1] for pin in component.pins]
        y_top, y_bottom = max(pin_ys), min(pin_ys)
    else:
        rows = [geo.line_y[r] for r in "ABCDEFGHIJ"]
        y_top, y_bottom = max(rows), min(rows)
    bx, by = first - 0.4, y_bottom - 0.3
    bw, bh = (last - first) + 0.8, (y_top - y_bottom) + 0.6
    axes.add_patch(
        Rectangle(
            (bx + 0.16, by - 0.22),
            bw,
            bh,
            facecolor=style.color(f"{section}.shadow"),
            edgecolor="none",
            alpha=0.4,
            zorder=6.6,
        )
    )
    axes.add_patch(
        Rectangle(
            (bx, by),
            bw,
            bh,
            facecolor=style.color(f"{section}.body"),
            edgecolor=style.color(f"{section}.body_edge"),
            linewidth=style.dim(f"{section}.body_edge_width"),
            zorder=7,
        )
    )
    # Lit top edge sells the raised chip body.
    axes.plot(
        [bx, bx + bw],
        [by + bh, by + bh],
        color=style.color(f"{section}.top_edge"),
        linewidth=style.dim(f"{section}.top_edge_width"),
        zorder=7.1,
    )
    axes.text(
        (first + last) / 2,
        (y_top + y_bottom) / 2,
        component.label,
        ha="center",
        va="center",
        fontsize=8.5,
        color=style.color(f"{section}.label"),
        fontweight="bold",
        zorder=8,
    )
    center_y = (y_top + y_bottom) / 2.0
    for pin in component.pins:
        px, py = geo.hole(pin.hole)
        axes.add_patch(
            Circle(
                (px, py),
                style.dim("dot.radius"),
                facecolor=style.color(f"{section}.pin"),
                edgecolor=style.color(f"{section}.body_edge"),
                linewidth=style.dim(f"{section}.pin_edge_width"),
                zorder=9,
            )
        )
        # Pins sit on the block edge; print names vertically into the body so
        # closely-spaced pins never overlap each other or the wires below.
        inward_up = py <= center_y
        axes.text(
            px,
            py + (0.28 if inward_up else -0.28),
            pin.name,
            ha="center",
            va="bottom" if inward_up else "top",
            rotation=90,
            fontsize=6.5,
            fontweight="bold",
            color=style.color(f"{section}.pin_label"),
            zorder=9,
        )
