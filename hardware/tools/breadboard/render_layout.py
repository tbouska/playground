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
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle

# Ordered vertical lines of the board, top to bottom. "" marks a blank gap slot.
LINE_ORDER: tuple[str, ...] = (
    "T+",
    "T-",
    "",
    "A",
    "B",
    "C",
    "D",
    "E",
    "",
    "F",
    "G",
    "H",
    "I",
    "J",
    "",
    "B+",
    "B-",
)
HOLE_RADIUS = 0.18
RENDER_DPI = 200
RAIL_PLUS_COLOR = "#c0392b"
RAIL_MINUS_COLOR = "#2c5fb3"
BOARD_COLOR = "#efeae0"
BOARD_EDGE = "#b7b0a0"
SHADOW_COLOR = "#8a8478"
HIGHLIGHT_COLOR = "#fbf8f1"
HOLE_FILL = "#dcd6ca"
HOLE_EDGE = "#a59e8c"
HOLE_SHADOW = "#c8c1af"
HOLE_HILITE = "#ebe6da"
# Connection-dot radius, shared by wires and every component lead/pin.
DOT_RADIUS = 0.13
# IEC resistor colour code, indexed by digit (0-9).
RESISTOR_DIGIT_COLORS = (
    "#1a1a1a", "#7a4a1e", "#c0392b", "#e67e22", "#f1c40f",
    "#27ae60", "#2c5fb3", "#8e44ad", "#7f8c8d", "#f2f2f2",
)
# Sub-unity multiplier bands and the 5-band tolerance band (brown = 1%).
RESISTOR_MULTIPLIER_EXTRA = {-1: "#cda434", -2: "#bfc1c2"}  # gold x0.1, silver x0.01
RESISTOR_TOLERANCE = "#7a4a1e"
GAP_COLOR = "#d2cabb"
GAP_SHADOW = "#a79f8d"
BODY_COLOR = "#e8e2d4"
CHANNEL_COLORS: dict[str, str] = {"R": "#c0392b", "G": "#27ae60", "B": "#2c5fb3"}
HOP_RADIUS = 0.22
# Board-coloured halo behind text so wires routed beneath cannot scratch it.
LABEL_BBOX: dict[str, Any] = {
    "boxstyle": "round,pad=0.18",
    "facecolor": BOARD_COLOR,
    "edgecolor": "none",
    "alpha": 0.82,
}
RAIL_ADDRESS = re.compile(r"^([TB][+-])(\d+)$")
GRID_ADDRESS = re.compile(r"^([A-J])(\d+)$")


@dataclass(frozen=True)
class Pin:
    """Describe a named module pin placed on a hole.

    :ivar name: The pin label, e.g. ``"GPIO0"``.
    :vartype name: str
    :ivar hole: The hole address the pin sits on, e.g. ``"J3"``.
    :vartype hole: str
    """

    name: str
    hole: str


@dataclass(frozen=True)
class Component:
    """Describe one placed component on the breadboard.

    :ivar kind: The component kind: ``module``, ``resistor``, ``led-rgb``,
        ``wire`` or ``power``.
    :vartype kind: str
    :ivar ref: The reference designator, or an empty string for wires.
    :vartype ref: str
    :ivar label: The display label, where applicable.
    :vartype label: str
    :ivar value: The component value, where applicable.
    :vartype value: str
    :ivar legs: The hole addresses for a two-leg part, in order.
    :vartype legs: tuple[str, ...]
    :ivar named_legs: The named-leg to hole mapping for an RGB LED.
    :vartype named_legs: dict[str, str]
    :ivar common: The RGB common type, ``cathode`` or ``anode``.
    :vartype common: str
    :ivar color: The wire color name.
    :vartype color: str
    :ivar endpoints: The two hole addresses of a wire, in order.
    :vartype endpoints: tuple[str, str]
    :ivar span: The inclusive column span ``(first, last)`` of a block.
    :vartype span: tuple[int, int]
    :ivar pins: The named pins of a module.
    :vartype pins: tuple[Pin, ...]
    """

    kind: str
    ref: str = ""
    label: str = ""
    value: str = ""
    legs: tuple[str, ...] = ()
    named_legs: dict[str, str] = field(default_factory=dict)
    common: str = "cathode"
    color: str = "black"
    endpoints: tuple[str, str] = ("", "")
    span: tuple[int, int] = (0, 0)
    pins: tuple[Pin, ...] = ()


@dataclass(frozen=True)
class Layout:
    """Describe a whole breadboard layout parsed from YAML.

    :ivar title: The layout title.
    :vartype title: str
    :ivar columns: The number of numbered columns on the board.
    :vartype columns: int
    :ivar components: The placed components.
    :vartype components: tuple[Component, ...]
    """

    title: str
    columns: int
    components: tuple[Component, ...]


def _component_from_dict(data: dict[str, Any]) -> Component:
    """Build a :class:`Component` from one parsed YAML mapping."""
    kind: str = data["kind"]
    pins = tuple(
        Pin(name=str(item["name"]), hole=str(item["hole"]))
        for item in data.get("pins", [])
    )
    named_legs: dict[str, str] = (
        {str(key): str(value) for key, value in data.get("legs", {}).items()}
        if isinstance(data.get("legs"), dict)
        else {}
    )
    legs: tuple[str, ...] = (
        tuple(str(item) for item in data["legs"])
        if isinstance(data.get("legs"), list)
        else ()
    )
    span_raw = data.get("span", [0, 0])
    return Component(
        kind=kind,
        ref=str(data.get("ref", "")),
        label=str(data.get("label", "")),
        value=str(data.get("value", "")),
        legs=legs,
        named_legs=named_legs,
        common=str(data.get("common", "cathode")),
        color=str(data.get("color", "black")),
        endpoints=(str(data.get("from", "")), str(data.get("to", ""))),
        span=(int(span_raw[0]), int(span_raw[1])),
        pins=pins,
    )


def load_layout(path: Path) -> Layout:
    """Parse a YAML hole-placement description into a :class:`Layout`.

    :param path: The path to the YAML description.
    :type path: Path
    :returns: The parsed layout.
    :rtype: Layout
    :raises KeyError: If a required key is missing from the description.
    """
    import yaml

    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    components = tuple(_component_from_dict(item) for item in data["components"])
    return Layout(
        title=str(data.get("title", "Breadboard layout")),
        columns=int(data["breadboard"]["columns"]),
        components=components,
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


def _draw_board(axes: plt.Axes, geo: Geometry) -> None:
    """Draw the board background, rails, holes, and row/column labels."""
    ys = list(geo.line_y.values())
    top, bottom = max(ys), min(ys)
    board_x, board_y = 0.2, bottom - 0.8
    board_w, board_h = geo.columns + 0.6, (top - bottom) + 1.6
    box = "round,pad=0,rounding_size=0.35"
    # Drop shadow lifts the board off the page; kept small so it stays clear
    # of the row/column legend printed just outside the board.
    axes.add_patch(
        FancyBboxPatch(
            (board_x + 0.12, board_y - 0.14),
            board_w,
            board_h,
            boxstyle=box,
            mutation_aspect=1.0,
            facecolor=SHADOW_COLOR,
            edgecolor="none",
            alpha=0.5,
            zorder=-1,
        )
    )
    axes.add_patch(
        FancyBboxPatch(
            (board_x, board_y),
            board_w,
            board_h,
            boxstyle=box,
            mutation_aspect=1.0,
            facecolor=BOARD_COLOR,
            edgecolor=BOARD_EDGE,
            linewidth=1.2,
            zorder=0,
        )
    )
    # Bevelled inner lip: a light edge inset from the rim reads as a raised face.
    axes.add_patch(
        FancyBboxPatch(
            (board_x + 0.16, board_y + 0.16),
            board_w - 0.32,
            board_h - 0.32,
            boxstyle="round,pad=0,rounding_size=0.7",
            mutation_aspect=1.0,
            facecolor="none",
            edgecolor=HIGHLIGHT_COLOR,
            linewidth=1.4,
            alpha=0.6,
            zorder=0.2,
        )
    )
    # Recessed centre channel: a groove *between* rows E and F, clear of holes.
    mid = (geo.line_y["E"] + geo.line_y["F"]) / 2.0
    chan_half = 0.55
    axes.add_patch(
        Rectangle(
            (board_x, mid - chan_half),
            board_w,
            2 * chan_half,
            facecolor=GAP_COLOR,
            edgecolor="none",
            zorder=0.5,
        )
    )
    axes.plot(
        [board_x, board_x + board_w],
        [mid + chan_half, mid + chan_half],
        color=GAP_SHADOW,
        linewidth=1.0,
        zorder=0.6,
    )
    axes.plot(
        [board_x, board_x + board_w],
        [mid - chan_half, mid - chan_half],
        color=HIGHLIGHT_COLOR,
        linewidth=1.0,
        alpha=0.7,
        zorder=0.6,
    )
    for key, y in geo.line_y.items():
        if key in ("T+", "B+"):
            axes.plot(
                [1, geo.columns], [y, y], color=RAIL_PLUS_COLOR, linewidth=1.2, zorder=1
            )
        if key in ("T-", "B-"):
            axes.plot(
                [1, geo.columns],
                [y, y],
                color=RAIL_MINUS_COLOR,
                linewidth=1.2,
                zorder=1,
            )
        side = HOLE_RADIUS * 1.7
        off = side * 0.1
        for col in range(1, geo.columns + 1):
            # Bevelled socket lit from the top-left, matching the board's drop
            # shadow: a faint highlight peeks out top-left and a faint shadow
            # bottom-right of the centred face, reading as pressed in.
            axes.add_patch(
                Rectangle(
                    (col - side / 2 - off, y - side / 2 + off),
                    side,
                    side,
                    facecolor=HOLE_HILITE,
                    edgecolor="none",
                    zorder=1.88,
                )
            )
            axes.add_patch(
                Rectangle(
                    (col - side / 2 + off, y - side / 2 - off),
                    side,
                    side,
                    facecolor=HOLE_SHADOW,
                    edgecolor="none",
                    zorder=1.9,
                )
            )
            axes.add_patch(
                Rectangle(
                    (col - side / 2, y - side / 2),
                    side,
                    side,
                    facecolor=HOLE_FILL,
                    edgecolor=HOLE_EDGE,
                    linewidth=0.4,
                    zorder=2,
                )
            )
        label = key
        if key in ("T+", "B+"):
            label = "+"
        elif key in ("T-", "B-"):
            label = "-"
        axes.text(0.0, y, label, ha="right", va="center", fontsize=8, color="#555")
        axes.text(
            geo.columns + 1.0,
            y,
            label,
            ha="left",
            va="center",
            fontsize=8,
            color="#555",
        )
    for col in range(1, geo.columns + 1):
        if col == 1 or col % 5 == 0:
            axes.text(
                col,
                top + 1.05,
                str(col),
                ha="center",
                va="bottom",
                fontsize=7,
                color="#777",
            )
            axes.text(
                col,
                bottom - 1.05,
                str(col),
                ha="center",
                va="top",
                fontsize=7,
                color="#777",
            )


def _leg_frame(
    p1: tuple[float, float], p2: tuple[float, float]
) -> tuple[float, float, float, float, float, float, float]:
    """Return axis unit ``(ux, uy)``, normal ``(nx, ny)``, midpoint and length."""
    (x1, y1), (x2, y2) = p1, p2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    return ux, uy, -uy, ux, (x1 + x2) / 2, (y1 + y2) / 2, length


def _draw_leads(
    axes: plt.Axes,
    p1: tuple[float, float],
    p2: tuple[float, float],
    ux: float,
    uy: float,
    body_half: float,
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Draw the two lead wires up to the body; return the body end points."""
    mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    e1 = (mx - ux * body_half, my - uy * body_half)
    e2 = (mx + ux * body_half, my + uy * body_half)
    axes.plot([p1[0], e1[0]], [p1[1], e1[1]], color="#555", linewidth=1.4, zorder=3)
    axes.plot([p2[0], e2[0]], [p2[1], e2[1]], color="#555", linewidth=1.4, zorder=3)
    return e1, e2


def _leg_dots(axes: plt.Axes, *holes: tuple[float, float]) -> None:
    """Mark each connection hole with a dot the same weight as wire ends."""
    for hx, hy in holes:
        axes.add_patch(
            Circle((hx, hy), DOT_RADIUS, facecolor="#444", edgecolor="none", zorder=5)
        )


def _part_label(
    axes: plt.Axes, x: float, y: float, nx: float, ny: float, ref: str, value: str
) -> None:
    """Print a part's reference (heavier) above its value (lighter)."""
    if value:
        axes.text(
            x + nx * 0.5, y + ny * 0.5, value,
            ha="center", va="center", fontsize=6.8, color="#5a5a5a",
            zorder=6, bbox=LABEL_BBOX,
        )
    if ref:
        axes.text(
            x + nx * 0.92, y + ny * 0.92, ref,
            ha="center", va="center", fontsize=8.5, fontweight="bold",
            color="#1f1f1f", zorder=6, bbox=LABEL_BBOX,
        )


def _body_quad(
    e1: tuple[float, float],
    e2: tuple[float, float],
    nx: float,
    ny: float,
    half_width: float,
) -> list[tuple[float, float]]:
    """Rectangle corners for a body running from ``e1`` to ``e2``."""
    return [
        (e1[0] + nx * half_width, e1[1] + ny * half_width),
        (e2[0] + nx * half_width, e2[1] + ny * half_width),
        (e2[0] - nx * half_width, e2[1] - ny * half_width),
        (e1[0] - nx * half_width, e1[1] - ny * half_width),
    ]


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


def _tint(color: str) -> tuple[float, float, float]:
    """Lighten a colour (name or hex) halfway to white for an LED lens."""
    r, g, b = to_rgb(color)
    return tuple(c + (1.0 - c) * 0.5 for c in (r, g, b))


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


def _block_rects(
    geo: Geometry, components: tuple[Component, ...]
) -> list[tuple[float, float, float, float]]:
    """Return ``(x_min, x_max, y_min, y_max)`` bounds of every drawn block."""
    rects: list[tuple[float, float, float, float]] = []
    for component in components:
        if component.kind not in ("module", "power"):
            continue
        first, last = component.span
        if component.pins:
            ys = [geo.hole(pin.hole)[1] for pin in component.pins]
        else:
            ys = [geo.line_y[r] for r in "ABCDEFGHIJ"]
        rects.append((first - 0.4, last + 0.4, min(ys) - 0.3, max(ys) + 0.3))
    return rects


def _hits_block(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    lane: float,
    blocks: list[tuple[float, float, float, float]],
) -> bool:
    """Whether routing ``x1 -> lane -> x2`` (VHV) would overlap any block."""
    segments = (
        (x1, x1, min(y1, lane), max(y1, lane)),
        (x2, x2, min(y2, lane), max(y2, lane)),
        (min(x1, x2), max(x1, x2), lane, lane),
    )
    return any(
        sx0 <= bx1 and sx1 >= bx0 and sy0 <= by1 and sy1 >= by0
        for bx0, bx1, by0, by1 in blocks
        for sx0, sx1, sy0, sy1 in segments
    )


def _wire_channels(geo: Geometry, components: tuple[Component, ...]) -> dict[int, float]:
    """Pick a right-angle routing lane for each diagonal wire.

    Wires sharing a row or column stay straight and get no lane. The rest
    route vertical-horizontal-vertical: through the centre gap when that path
    is clear, otherwise through the margin below the banks so the wire skirts
    blocks instead of crossing them. Within a lane, wider wires sit further
    out so nested fan-outs do not cross each other.

    ponytail: lanes spread by a fixed step; non-nested fan-outs, or more wires
    than the margin holds, would still need a real channel router.
    """
    blocks = _block_rects(geo, components)
    diagonal = [
        c
        for c in components
        if c.kind == "wire"
        and geo.hole(c.endpoints[0])[0] != geo.hole(c.endpoints[1])[0]
        and geo.hole(c.endpoints[0])[1] != geo.hole(c.endpoints[1])[1]
    ]
    gap_y = (geo.line_y["E"] + geo.line_y["F"]) / 2.0
    below_y = (geo.line_y["J"] + geo.line_y["B+"]) / 2.0
    step = 0.5

    base: dict[int, float] = {}
    for c in diagonal:
        x1, y1 = geo.hole(c.endpoints[0])
        x2, y2 = geo.hole(c.endpoints[1])
        base[id(c)] = (
            gap_y if not _hits_block(x1, y1, x2, y2, gap_y, blocks) else below_y
        )

    channels: dict[int, float] = {}
    for lane in set(base.values()):
        members = [c for c in diagonal if base[id(c)] == lane]
        members.sort(
            key=lambda c: abs(
                geo.hole(c.endpoints[1])[0] - geo.hole(c.endpoints[0])[0]
            ),
            reverse=True,
        )
        count = len(members)
        for index, c in enumerate(members):
            channels[id(c)] = lane + (index - (count - 1) / 2.0) * step
    return channels


def _wire_points(
    geo: Geometry, component: Component, channel_y: float | None
) -> list[tuple[float, float]]:
    """Right-angle (VHV) polyline for a wire, or a straight segment.

    Holes sharing a row or column (``channel_y`` is None) give a straight
    segment; otherwise the wire drops to ``channel_y``, runs across, and rises.
    """
    x1, y1 = geo.hole(component.endpoints[0])
    x2, y2 = geo.hole(component.endpoints[1])
    if channel_y is None or x1 == x2 or y1 == y2:
        return [(x1, y1), (x2, y2)]
    return [(x1, y1), (x1, channel_y), (x2, channel_y), (x2, y2)]


def _hop_polyline(
    xa: float, xb: float, y: float, crossings: list[float], steps: int = 8
) -> tuple[list[float], list[float]]:
    """Horizontal run ``xa->xb`` at ``y`` that bumps over each crossing x."""
    rightward = xb >= xa
    ordered = crossings if rightward else list(reversed(crossings))
    xs, ys = [xa], [y]
    for cx in ordered:
        for step in range(steps + 1):
            theta = math.pi * (1 - step / steps if rightward else step / steps)
            xs.append(cx + HOP_RADIUS * math.cos(theta))
            ys.append(y + HOP_RADIUS * math.sin(theta))
    xs.append(xb)
    ys.append(y)
    return xs, ys


def _draw_wire(
    axes: plt.Axes,
    component: Component,
    points: list[tuple[float, float]],
    verticals: list[tuple[float, float, float, int]],
) -> None:
    """Draw one wire's polyline, hopping its horizontal runs over verticals."""
    for (xa, ya), (xb, yb) in zip(points, points[1:]):
        if abs(xa - xb) < 1e-9:
            xs, ys = [xa, xb], [ya, yb]
        else:
            crossings = sorted(
                vx
                for vx, vlo, vhi, owner in verticals
                if owner != id(component)
                and min(xa, xb) + 1e-6 < vx < max(xa, xb) - 1e-6
                and vlo + 1e-6 < ya < vhi - 1e-6
            )
            xs, ys = _hop_polyline(xa, xb, ya, crossings)
        axes.plot(
            xs,
            ys,
            color=component.color,
            linewidth=2.0,
            solid_capstyle="round",
            solid_joinstyle="round",
            zorder=3.5,
            alpha=0.9,
        )
    for hx, hy in (points[0], points[-1]):
        axes.add_patch(
            Circle(
                (hx, hy), DOT_RADIUS, facecolor=component.color, edgecolor="none", zorder=5
            )
        )


def _draw_wires(
    axes: plt.Axes,
    geo: Geometry,
    components: tuple[Component, ...],
    channels: dict[int, float],
) -> None:
    """Draw every wire, annotating non-connecting crossings with hop bumps."""
    paths = [
        (c, _wire_points(geo, c, channels.get(id(c))))
        for c in components
        if c.kind == "wire"
    ]
    verticals: list[tuple[float, float, float, int]] = []
    for component, points in paths:
        for (xa, ya), (xb, yb) in zip(points, points[1:]):
            if abs(xa - xb) < 1e-9:
                verticals.append((xa, min(ya, yb), max(ya, yb), id(component)))
    for component, points in paths:
        _draw_wire(axes, component, points, verticals)


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
