"""Render a breadboard hole-placement layout from a declarative YAML file.

This module reads a hole-placement description (components addressed to specific
breadboard holes such as ``F12`` or rail holes such as ``B-28``) and draws a
realistic breadboard with power rails, the A-J banks, the center gap and
numbered columns, then places each component on its addressed holes. Output is
SVG and PNG, matching the schematic renderer so both views build the same way.

Imports:
    math -- compute lead and body geometry for two-leg components.
    re -- parse hole addresses into row and column parts.
    sys -- read the optional YAML path from the command line.
    dataclasses -- model the parsed layout as frozen value objects.
    pathlib -- resolve input and output file paths.
    typing -- supply :class:`Any` for the untyped parsed YAML mapping.
    matplotlib -- force the headless ``Agg`` backend, then draw with
        :mod:`matplotlib.pyplot` and :mod:`matplotlib.patches`.
    yaml -- parse the description with :func:`yaml.safe_load`.
"""

# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "matplotlib>=3.8",
#     "pyyaml>=6.0",
# ]
# ///

import math
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle

from breadboard.geometry import GRID_ADDRESS, LINE_ORDER, RAIL_ADDRESS, Geometry
from breadboard.model import Component, Layout, Pin
from breadboard.parse import load_layout, _component_from_dict
from breadboard.style import (
    BOARD_COLOR,
    BOARD_EDGE,
    BODY_COLOR,
    CHANNEL_COLORS,
    DOT_RADIUS,
    GAP_COLOR,
    GAP_SHADOW,
    HIGHLIGHT_COLOR,
    HOLE_EDGE,
    HOLE_FILL,
    HOLE_HILITE,
    HOLE_RADIUS,
    HOLE_SHADOW,
    HOP_RADIUS,
    LABEL_BBOX,
    RAIL_MINUS_COLOR,
    RAIL_PLUS_COLOR,
    RENDER_DPI,
    RESISTOR_DIGIT_COLORS,
    RESISTOR_MULTIPLIER_EXTRA,
    RESISTOR_TOLERANCE,
    SHADOW_COLOR,
)
from breadboard.board import _draw_board
from breadboard.wires import (
    _block_rects,
    _hits_block,
    _wire_channels,
    _wire_points,
    _hop_polyline,
    _draw_wire,
    _draw_wires,
)
from breadboard.components.base import (
    _leg_frame,
    _draw_leads,
    _leg_dots,
    _part_label,
    _body_quad,
    _tint,
)




class Geometry:
    """Map hole addresses to drawing coordinates for a board width.

    :ivar columns: The number of numbered columns.
    :vartype columns: int
    :ivar line_y: The y coordinate of each named line.
    :vartype line_y: dict[str, float]
    """

    def __init__(self, columns: int) -> None:
        """Build the geometry for a board with the given column count.

        :param columns: The number of numbered columns.
        :type columns: int
        """
        self.columns = columns
        self.line_y = {
            key: -float(index) for index, key in enumerate(LINE_ORDER) if key
        }

    def hole(self, address: str) -> tuple[float, float]:
        """Resolve a hole address to an ``(x, y)`` coordinate.

        :param address: A hole address such as ``"F12"`` or ``"B-28"``.
        :type address: str
        :returns: The coordinate of the hole center.
        :rtype: tuple[float, float]
        :raises ValueError: If the address does not match a known hole.
        """
        rail = RAIL_ADDRESS.match(address)
        if rail:
            return float(rail.group(2)), self.line_y[rail.group(1)]
        grid = GRID_ADDRESS.match(address)
        if grid:
            return float(grid.group(2)), self.line_y[grid.group(1)]
        raise ValueError(f"invalid hole address: {address!r}")


def _parse_ohms(value: str) -> float | None:
    """Parse a resistor value like ``220``, ``4.7k`` or ``1M`` into ohms."""
    text = value.strip().lower().replace("ω", "").replace("ohm", "").replace(" ", "")
    if not text:
        return None
    multiplier = 1.0
    if text[-1] == "k":
        multiplier, text = 1e3, text[:-1]
    elif text[-1] == "m":
        multiplier, text = 1e6, text[:-1]
    elif text[-1] == "r":
        text = text[:-1]
    try:
        return float(text) * multiplier
    except ValueError:
        return None


def _format_ohms(value: str) -> str:
    """Format a resistor value with the ohm symbol (``220 Ω``, ``4.7 kΩ``)."""
    ohms = _parse_ohms(value)
    if ohms is None:
        return value
    if ohms >= 1e6:
        return f"{ohms / 1e6:g} MΩ"
    if ohms >= 1e3:
        return f"{ohms / 1e3:g} kΩ"
    return f"{ohms:g} Ω"


def _resistor_bands(value: str) -> list[str] | None:
    """Five-band colour code (three digits, multiplier, tolerance) for a value."""
    ohms = _parse_ohms(value)
    if ohms is None or ohms <= 0:
        return None
    exponent = math.floor(math.log10(ohms))
    mantissa = round(ohms / 10 ** (exponent - 2))
    if mantissa >= 1000:
        mantissa //= 10
        exponent += 1
    digits = (mantissa // 100, (mantissa // 10) % 10, mantissa % 10)
    multiplier = exponent - 2
    if 0 <= multiplier <= 9:
        multiplier_color = RESISTOR_DIGIT_COLORS[multiplier]
    elif multiplier in RESISTOR_MULTIPLIER_EXTRA:
        multiplier_color = RESISTOR_MULTIPLIER_EXTRA[multiplier]
    else:
        return None
    return [RESISTOR_DIGIT_COLORS[d] for d in digits] + [
        multiplier_color,
        RESISTOR_TOLERANCE,
    ]


def _resistor(axes: plt.Axes, geo: Geometry, component: Component) -> None:
    """Draw a resistor: leads, tan body, colour-code bands and labels."""
    p1, p2 = geo.hole(component.legs[0]), geo.hole(component.legs[1])
    ux, uy, nx, ny, mx, my, length = _leg_frame(p1, p2)
    body_half = min(0.32 * length, 0.55)
    width = 0.22
    e1, e2 = _draw_leads(axes, p1, p2, ux, uy, body_half)
    axes.add_patch(
        Polygon(
            _body_quad(e1, e2, nx, ny, width),
            closed=True,
            facecolor=BODY_COLOR,
            edgecolor="#7a7466",
            linewidth=1.0,
            zorder=4,
        )
    )
    bands = _resistor_bands(component.value)
    if bands:
        band_w = body_half * 0.12
        for index, color in enumerate(bands):
            frac = (index + 1) / (len(bands) + 1)
            bx = e1[0] + (e2[0] - e1[0]) * frac
            by = e1[1] + (e2[1] - e1[1]) * frac
            stripe = (bx - ux * band_w, by - uy * band_w)
            stripe2 = (bx + ux * band_w, by + uy * band_w)
            axes.add_patch(
                Polygon(
                    _body_quad(stripe, stripe2, nx, ny, width),
                    closed=True,
                    facecolor=color,
                    edgecolor="none",
                    zorder=4.5,
                )
            )
    _leg_dots(axes, p1, p2)
    _part_label(axes, mx, my, nx, ny, component.ref, _format_ohms(component.value))


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


def _led(axes: plt.Axes, geo: Geometry, component: Component) -> None:
    """Draw an RGB LED (named legs) or a single LED (two ordered legs)."""
    if component.named_legs:
        leads = [
            (CHANNEL_COLORS.get(name, "#888"), geo.hole(hole))
            for name, hole in component.named_legs.items()
        ]
        lens_fill = "#f6d9d2"
        caption = f"{component.ref} RGB ({'CC' if component.common == 'cathode' else 'CA'})"
    else:
        leads = [
            ("#888", geo.hole(component.legs[0])),
            ("#888", geo.hole(component.legs[1])),
        ]
        lens_fill = _tint(component.color)
        caption = component.ref
    holes = [point for _, point in leads]
    cx = sum(hx for hx, _ in holes) / len(holes)
    cy = max(hy for _, hy in holes) + 0.95
    radius = 0.5
    for color, (hx, hy) in leads:
        axes.plot([hx, cx], [hy, cy], color=color, linewidth=1.6, zorder=3)
    _leg_dots(axes, *holes)
    _led_lens(axes, cx, cy, radius, lens_fill)
    axes.text(
        cx, cy + radius + 0.28, caption,
        ha="center", va="bottom", fontsize=8.0, fontweight="bold",
        color="#1f1f1f", zorder=6, bbox=LABEL_BBOX,
    )


def _capacitor(axes: plt.Axes, geo: Geometry, component: Component) -> None:
    """Draw a ceramic (disc) or electrolytic (striped cylinder) capacitor."""
    p1, p2 = geo.hole(component.legs[0]), geo.hole(component.legs[1])
    ux, uy, nx, ny, mx, my, length = _leg_frame(p1, p2)
    polar = component.common.strip().lower() in (
        "anode", "polar", "polarized", "electrolytic", "+",
    )
    if polar:
        body_half = min(0.34 * length, 0.5)
        width = 0.34
        e1, e2 = _draw_leads(axes, p1, p2, ux, uy, body_half)
        axes.add_patch(
            Polygon(
                _body_quad(e1, e2, nx, ny, width),
                closed=True, facecolor="#2c3e6b", edgecolor="#1c2747",
                linewidth=1.0, zorder=4,
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
                closed=True, facecolor="#dfe6f2", edgecolor="none", zorder=4.5,
            )
        )
    else:
        body_half = min(0.28 * length, 0.36)
        e1, e2 = _draw_leads(axes, p1, p2, ux, uy, body_half)
        axes.add_patch(
            Circle(
                ((e1[0] + e2[0]) / 2, (e1[1] + e2[1]) / 2),
                0.34, facecolor="#d9a441", edgecolor="#9c7320",
                linewidth=1.0, zorder=4,
            )
        )
    _leg_dots(axes, p1, p2)
    _part_label(axes, mx, my, nx, ny, component.ref, component.value)


def _diode(axes: plt.Axes, geo: Geometry, component: Component) -> None:
    """Draw a diode body with a cathode band on the second leg."""
    p1, p2 = geo.hole(component.legs[0]), geo.hole(component.legs[1])
    ux, uy, nx, ny, mx, my, length = _leg_frame(p1, p2)
    body_half = min(0.32 * length, 0.5)
    width = 0.18
    e1, e2 = _draw_leads(axes, p1, p2, ux, uy, body_half)
    axes.add_patch(
        Polygon(
            _body_quad(e1, e2, nx, ny, width),
            closed=True, facecolor="#2b2b2b", edgecolor="#111111",
            linewidth=1.0, zorder=4,
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
            closed=True, facecolor="#d8d8d8", edgecolor="none", zorder=4.5,
        )
    )
    _leg_dots(axes, p1, p2)
    _part_label(axes, mx, my, nx, ny, component.ref, component.value)


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


def _button(axes: plt.Axes, geo: Geometry, component: Component) -> None:
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
    _leg_dots(axes, *holes)
    axes.text(
        cx, y1 + 0.2,
        " ".join(p for p in (component.ref, component.value) if p),
        ha="center", va="bottom", fontsize=8.0, fontweight="bold",
        color="#1f1f1f", zorder=6, bbox=LABEL_BBOX,
    )


def _block(axes: plt.Axes, geo: Geometry, component: Component) -> None:
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
            facecolor="#1f262c",
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
            facecolor="#5b6770",
            edgecolor="#39424a",
            linewidth=1.0,
            zorder=7,
        )
    )
    # Lit top edge sells the raised chip body.
    axes.plot(
        [bx, bx + bw],
        [by + bh, by + bh],
        color="#7c8893",
        linewidth=1.6,
        zorder=7.1,
    )
    axes.text(
        (first + last) / 2,
        (y_top + y_bottom) / 2,
        component.label,
        ha="center",
        va="center",
        fontsize=8.5,
        color="white",
        fontweight="bold",
        zorder=8,
    )
    center_y = (y_top + y_bottom) / 2.0
    for pin in component.pins:
        px, py = geo.hole(pin.hole)
        axes.add_patch(
            Circle(
                (px, py),
                DOT_RADIUS,
                facecolor="#ffd166",
                edgecolor="#39424a",
                linewidth=0.6,
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
            color="white",
            zorder=9,
        )


def render(layout: Layout, out_stem: Path) -> None:
    """Render a layout to ``<stem>.svg`` and ``<stem>.png``.

    :param layout: The layout to render.
    :type layout: Layout
    :param out_stem: The output path without extension.
    :type out_stem: Path
    :returns: None. The function writes the two image files to disk.
    :rtype: None
    """
    geo = Geometry(layout.columns)
    width = max(8.0, layout.columns * 0.42)
    figure, axes = plt.subplots(figsize=(width, 6.5))
    _draw_board(axes, geo)

    channels = _wire_channels(geo, layout.components)
    _draw_wires(axes, geo, layout.components, channels)
    drawers = {
        "resistor": _resistor,
        "led-rgb": _led,
        "led": _led,
        "capacitor": _capacitor,
        "diode": _diode,
        "transistor": _transistor,
        "button": _button,
        "module": _block,
        "power": _block,
    }
    for component in layout.components:
        drawer = drawers.get(component.kind)
        if drawer is not None:
            drawer(axes, geo, component)

    axes.set_title(layout.title, fontsize=12, color="#222")
    axes.set_aspect("equal")
    axes.axis("off")
    axes.autoscale_view()
    figure.tight_layout()
    figure.savefig(out_stem.with_suffix(".svg"))
    figure.savefig(out_stem.with_suffix(".png"), dpi=RENDER_DPI)
    plt.close(figure)


def main() -> None:
    """Parse the YAML path from the command line and render the layout.

    :returns: None. The function writes the rendered image files to disk.
    :rtype: None
    """
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("layout.yaml")
    render(load_layout(source), source.with_suffix(""))


if __name__ == "__main__":
    main()
