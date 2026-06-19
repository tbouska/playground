"""Wire routing and drawing helpers."""

import math

import matplotlib.pyplot as plt
from matplotlib.patches import Circle

from breadboard.geometry import Geometry
from breadboard.model import Component
from breadboard.style import DOT_RADIUS, HOP_RADIUS


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
