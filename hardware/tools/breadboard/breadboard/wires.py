"""Route and draw jumper wires.

Wires render *above* every component (component zorders top out at 9) so that a
wire forced to cross a part lies visibly over it instead of hiding behind it.
Each wire is routed to avoid component footprints where it can: the router
treats every drawn part as an obstacle box and searches simple orthogonal paths
(straight, right-angle detour, and lane routes that escape a boxed-in endpoint
sideways before running a clear lane), picking the one that crosses the fewest
parts. Wires sharing a lane are fanned apart, and horizontal runs hop over the
vertical segments of other wires so crossings read as jumps, not joins.
"""

import math

import matplotlib.pyplot as plt
from matplotlib.patches import Circle

from breadboard.geometry import Geometry
from breadboard.model import Component
from breadboard.style import Style

# Wires sit above every component; component zorders top out at 9 (module pins).
_WIRE_ZORDER = 10.0
_WIRE_DOT_ZORDER = 10.5

# Padding around a component's holes when treated as a routing obstacle.
_OBSTACLE_PAD = 0.5
# An LED lens rises ~1.45 above its leg row; pad the box up so wires skirt it.
_LED_BODY_RISE = 1.6
# Vertical spacing between wires that end up sharing one routing lane.
_SPREAD_STEP = 0.5

Rect = tuple[float, float, float, float]
Point = tuple[float, float]


def _component_holes(component: Component) -> list[str]:
    """Every hole address a component occupies (legs, named legs, pins)."""
    return (
        list(component.legs)
        + list(component.named_legs.values())
        + [pin.hole for pin in component.pins]
    )


def _component_rects(geo: Geometry, components: tuple[Component, ...]) -> list[Rect]:
    """Axis-aligned obstacle box ``(x0, x1, y0, y1)`` for each non-wire part."""
    rects: list[Rect] = []
    for component in components:
        if component.kind == "wire":
            continue
        holes = _component_holes(component)
        xs = [geo.hole(h)[0] for h in holes]
        ys = [geo.hole(h)[1] for h in holes]
        if component.kind in ("module", "power"):
            first, last = component.span
            xs += [first, last]
            if not component.pins:
                ys += [geo.line_y[r] for r in "ABCDEFGHIJ"]
        if not xs:
            continue
        y_hi = max(ys) + (_LED_BODY_RISE if component.kind in ("led", "led-rgb") else _OBSTACLE_PAD)
        rects.append((min(xs) - _OBSTACLE_PAD, max(xs) + _OBSTACLE_PAD, min(ys) - _OBSTACLE_PAD, y_hi))
    return rects


def _seg_hits_rect(xa: float, ya: float, xb: float, yb: float, rect: Rect) -> bool:
    """Whether the axis-aligned segment ``(xa,ya)-(xb,yb)`` overlaps ``rect``."""
    bx0, bx1, by0, by1 = rect
    return (
        min(xa, xb) <= bx1
        and max(xa, xb) >= bx0
        and min(ya, yb) <= by1
        and max(ya, yb) >= by0
    )


def _segments(points: list[Point]) -> list[tuple[Point, Point]]:
    return list(zip(points, points[1:]))


def _dedupe(points: list[Point]) -> list[Point]:
    """Drop consecutive duplicate points (zero-length segments)."""
    out: list[Point] = []
    for p in points:
        if not out or abs(p[0] - out[-1][0]) > 1e-9 or abs(p[1] - out[-1][1]) > 1e-9:
            out.append(p)
    return out


def _path_len(points: list[Point]) -> float:
    return sum(math.hypot(xb - xa, yb - ya) for (xa, ya), (xb, yb) in _segments(points))


def _crossings(points: list[Point], rects: list[Rect]) -> int:
    """Count distinct obstacle rects any segment of the path overlaps."""
    return sum(
        1
        for rect in rects
        if any(_seg_hits_rect(xa, ya, xb, yb, rect) for (xa, ya), (xb, yb) in _segments(points))
    )


def _lanes(geo: Geometry) -> tuple[float, ...]:
    """Clear horizontal corridors: centre gap, below the banks, above row A."""
    gap = (geo.line_y["E"] + geo.line_y["F"]) / 2.0
    below = (geo.line_y["J"] + geo.line_y["B+"]) / 2.0
    above = geo.line_y["A"] + 1.0
    return (gap, below, above)


def _corridor_columns(geo: Geometry, rects: list[Rect], x1: float, x2: float) -> list[float]:
    """Vertical-corridor x candidates: the endpoints and each obstacle's flanks."""
    lo, hi = 0.5, geo.columns + 0.5
    cols = {x1, x2}
    for bx0, bx1, _by0, _by1 in rects:
        cols.add(min(max(bx0 - 0.5, lo), hi))
        cols.add(min(max(bx1 + 0.5, lo), hi))
    return sorted(cols)


def _candidate_paths(geo: Geometry, p1: Point, p2: Point, rects: list[Rect]) -> list[list[Point]]:
    """Orthogonal route candidates from ``p1`` to ``p2`` to score and pick from."""
    x1, y1 = p1
    x2, y2 = p2
    cols = _corridor_columns(geo, rects, x1, x2)
    lanes = _lanes(geo)
    paths: list[list[Point]] = [[p1, p2]]
    for ex in cols:
        paths.append([p1, (ex, y1), (ex, y2), p2])  # horizontal-vertical-horizontal detour
    for lane in lanes:
        paths.append([p1, (x1, lane), (x2, lane), p2])  # vertical-horizontal-vertical
        for ex1 in cols:
            for ex2 in cols:
                # Escape each endpoint sideways to a clear column, then run the lane.
                paths.append([p1, (ex1, y1), (ex1, lane), (ex2, lane), (ex2, y2), p2])
    return paths


def _on_grid_run(geo: Geometry, points: list[Point]) -> float:
    """Total length of horizontal runs that lie along a hole row (A-J).

    Long horizontal runs read cleanest in the off-grid lanes (centre gap, below
    the banks, above row A); penalising on-row runs steers the router there
    rather than dragging a wire across a row of holes.
    """
    grid_ys = [geo.line_y[r] for r in "ABCDEFGHIJ"]
    total = 0.0
    for (xa, ya), (xb, yb) in _segments(points):
        if abs(ya - yb) < 1e-9 and any(abs(ya - gy) < 0.3 for gy in grid_ys):
            total += abs(xb - xa)
    return total


def _route(geo: Geometry, component: Component, rects: list[Rect]) -> list[Point]:
    """Pick the route crossing the fewest parts, off grid rows, short, simple."""
    p1 = geo.hole(component.endpoints[0])
    p2 = geo.hole(component.endpoints[1])
    # A direct hop that touches nothing wins outright -- never detour a clean wire.
    straight = _dedupe([p1, p2])
    if _crossings(straight, rects) == 0:
        return straight
    best_key: tuple[int, float, int] | None = None
    best_path: list[Point] = straight
    for raw in _candidate_paths(geo, p1, p2, rects):
        path = _dedupe(raw)
        # Cost trades length against on-row distance 1:1, so the router shuns long
        # runs across hole rows but won't loop the board to save a short stub.
        key = (
            _crossings(path, rects),
            round(_path_len(path) + _on_grid_run(geo, path), 3),
            len(path),
        )
        if best_key is None or key < best_key:
            best_key, best_path = key, path
    return best_path


def _path_lane(points: list[Point], y1: float, y2: float) -> float | None:
    """The y of the longest horizontal run that is a true lane (not an endpoint row)."""
    best_y: float | None = None
    best_run = 0.0
    for (xa, ya), (xb, yb) in _segments(points):
        if abs(ya - yb) > 1e-9:
            continue
        if abs(ya - y1) < 1e-9 or abs(ya - y2) < 1e-9:
            continue
        run = abs(xb - xa)
        if run > best_run:
            best_run, best_y = run, ya
    return best_y


def _shift_lane(points: list[Point], lane: float, offset: float) -> list[Point]:
    """Move every point sitting on ``lane`` by ``offset`` so the lane fans apart."""
    return [(x, y + offset if abs(y - lane) < 1e-9 else y) for x, y in points]


def _spread(geo: Geometry, components: tuple[Component, ...], routes: dict[int, list[Point]]) -> None:
    """Fan apart wires that ended up sharing a routing lane, widest run outermost."""
    ends = {
        id(c): (geo.hole(c.endpoints[0]), geo.hole(c.endpoints[1]))
        for c in components
        if c.kind == "wire"
    }
    groups: dict[float, list[int]] = {}
    for wid, path in routes.items():
        (_x1, y1), (_x2, y2) = ends[wid]
        lane = _path_lane(path, y1, y2)
        if lane is not None:
            groups.setdefault(round(lane, 3), []).append(wid)
    for lane, members in groups.items():
        if len(members) < 2:
            continue
        members.sort(key=lambda wid: -abs(routes[wid][0][0] - routes[wid][-1][0]))
        count = len(members)
        for index, wid in enumerate(members):
            offset = (index - (count - 1) / 2.0) * _SPREAD_STEP
            routes[wid] = _shift_lane(routes[wid], lane, offset)


def _wire_channels(geo: Geometry, components: tuple[Component, ...]) -> dict[int, list[Point]]:
    """Route every wire around component footprints; return id -> polyline."""
    rects = _component_rects(geo, components)
    routes = {id(c): _route(geo, c, rects) for c in components if c.kind == "wire"}
    _spread(geo, components, routes)
    return routes


def _hop_polyline(
    xa: float, xb: float, y: float, crossings: list[float], hop_radius: float, steps: int = 8
) -> tuple[list[float], list[float]]:
    """Horizontal run ``xa->xb`` at ``y`` that bumps over each crossing x."""
    rightward = xb >= xa
    ordered = crossings if rightward else list(reversed(crossings))
    xs, ys = [xa], [y]
    for cx in ordered:
        for step in range(steps + 1):
            theta = math.pi * (1 - step / steps if rightward else step / steps)
            xs.append(cx + hop_radius * math.cos(theta))
            ys.append(y + hop_radius * math.sin(theta))
    xs.append(xb)
    ys.append(y)
    return xs, ys


def _draw_wire(
    axes: plt.Axes,
    component: Component,
    points: list[Point],
    verticals: list[tuple[float, float, float, int]],
    style: Style,
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
            xs, ys = _hop_polyline(xa, xb, ya, crossings, style.dim("hop.radius"))
        axes.plot(
            xs,
            ys,
            color=component.color,
            linewidth=style.dim("wire.width"),
            solid_capstyle="round",
            solid_joinstyle="round",
            zorder=_WIRE_ZORDER,
            alpha=0.9,
        )
    for hx, hy in (points[0], points[-1]):
        axes.add_patch(
            Circle(
                (hx, hy), style.dim("dot.radius"), facecolor=component.color, edgecolor="none", zorder=_WIRE_DOT_ZORDER
            )
        )


def _draw_wires(
    axes: plt.Axes,
    geo: Geometry,
    components: tuple[Component, ...],
    channels: dict[int, list[Point]],
    style: Style,
) -> None:
    """Draw every wire, annotating non-connecting crossings with hop bumps."""
    paths = [(c, channels[id(c)]) for c in components if c.kind == "wire"]
    verticals: list[tuple[float, float, float, int]] = []
    for component, points in paths:
        for (xa, ya), (xb, yb) in zip(points, points[1:]):
            if abs(xa - xb) < 1e-9:
                verticals.append((xa, min(ya, yb), max(ya, yb), id(component)))
    for component, points in paths:
        _draw_wire(axes, component, points, verticals, style)
