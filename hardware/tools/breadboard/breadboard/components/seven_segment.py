import logging

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, Rectangle

from breadboard.components import register
from breadboard.geometry import Geometry
from breadboard.model import Component
from breadboard.style import Style

_log = logging.getLogger("breadboard")

# Classic 7-segment a–g layout, plus DP.
# Each segment is a thin parallelogram defined in a local coordinate system
# centred on (0, 0) with height ~2.0 and width ~1.0.
# Segment order: a (top), b (top-right), c (bottom-right), d (bottom),
#                e (bottom-left), f (top-left), g (middle).
_T = 0.10   # half-thickness of a segment bar
_W = 0.36   # half-width of a horizontal segment
_SX = 0.40  # x half-extent of the digit
_SY = 0.40  # y half-extent of the digit

_SEGMENTS = [
    # a: top horizontal
    [(-_W, _SY - _T), (_W, _SY - _T), (_W, _SY + _T), (-_W, _SY + _T)],
    # b: top-right vertical
    [(_SX - _T, _T), (_SX + _T, _T), (_SX + _T, _SY), (_SX - _T, _SY)],
    # c: bottom-right vertical
    [(_SX - _T, -_SY), (_SX + _T, -_SY), (_SX + _T, -_T), (_SX - _T, -_T)],
    # d: bottom horizontal
    [(-_W, -_SY - _T), (_W, -_SY - _T), (_W, -_SY + _T), (-_W, -_SY + _T)],
    # e: bottom-left vertical
    [(-_SX - _T, -_SY), (-_SX + _T, -_SY), (-_SX + _T, -_T), (-_SX - _T, -_T)],
    # f: top-left vertical
    [(-_SX - _T, _T), (-_SX + _T, _T), (-_SX + _T, _SY), (-_SX - _T, _SY)],
    # g: middle horizontal
    [(-_W, -_T), (_W, -_T), (_W, _T), (-_W, _T)],
]

_DP_CENTER = (_SX + 0.18, -_SY - _T)
_DP_RADIUS = _T * 0.9

# Fixed scale: digit fits in a ~1.0 unit box (independent of pin spread).
_DIGIT_SCALE = 0.55


def _seven_segment_extent(
    axes: plt.Axes, geo: Geometry, component: Component
) -> tuple[float, float, float, float]:
    # Returns (x_left, x_right, y_top, y_bottom).
    if component.pins:
        pin_coords = [geo.hole(p.hole) for p in component.pins]
        xs, ys = zip(*pin_coords)
        y_top, y_bottom = max(ys), min(ys)
        x_left, x_right = min(xs), max(xs)
    else:
        first, last = component.span
        _log.warning("seven_segment %r has no pins; rendering body from span %s", component.ref, component.span)
        x_left, x_right = float(first), float(last)
        rows = [geo.line_y[r] for r in "ABCDEFGHIJ"]
        y_top, y_bottom = max(rows), min(rows)
    return x_left, x_right, y_top, y_bottom


def _digit_centers(
    cx: float, bx: float, bw: float, n_digits: int, s: float
) -> tuple[list[float], float, float]:
    # Returns (digit_centers, bx, bw).
    if n_digits == 1:
        digit_centers = [cx]
    else:
        pitch = (2.0 * _SX + 0.30) * s
        row_w = pitch * (n_digits - 1)
        needed = row_w + 2.0 * _SX * s
        interior = bw - 0.8
        if needed > interior:
            extra = needed - interior
            bx -= extra / 2.0
            bw += extra
        first_cx = cx - row_w / 2.0
        digit_centers = [first_cx + i * pitch for i in range(n_digits)]
    return digit_centers, bx, bw


def _draw_digit(axes: plt.Axes, dcx: float, cy: float, s: float, style: Style) -> None:
    # Draws one digit (segments + decimal point) at (dcx, cy).
    for seg_verts in _SEGMENTS:
        axes.add_patch(
            Polygon(
                [(dcx + s * vx, cy + s * vy) for vx, vy in seg_verts],
                closed=True,
                facecolor=style.color("seven_segment.segment"),
                edgecolor=style.color("seven_segment.segment_edge"),
                linewidth=style.dim("seven_segment.segment_edge_width"),
                zorder=8,
            )
        )

    dp_x = dcx + s * _DP_CENTER[0]
    dp_y = cy + s * _DP_CENTER[1]
    axes.add_patch(
        Circle(
            (dp_x, dp_y),
            s * _DP_RADIUS,
            facecolor=style.color("seven_segment.dp"),
            edgecolor="none",
            zorder=8,
        )
    )


def _seven_segment_pins(axes: plt.Axes, geo: Geometry, component: Component, style: Style) -> None:
    # Draw a dot at each pin hole.
    for px, py in (geo.hole(p.hole) for p in component.pins):
        axes.add_patch(
            Circle(
                (px, py),
                style.dim("dot.radius"),
                facecolor=style.color("seven_segment.pin"),
                edgecolor=style.color("seven_segment.pin_edge"),
                linewidth=style.dim("seven_segment.pin_edge_width"),
                zorder=9,
            )
        )


@register("7segment")
def draw_seven_segment(axes: plt.Axes, geo: Geometry, component: Component, style: Style) -> None:
    x_left, x_right, y_top, y_bottom = _seven_segment_extent(axes, geo, component)
    cx = (x_left + x_right) / 2.0
    cy = (y_top + y_bottom) / 2.0
    s = _DIGIT_SCALE

    bx = x_left - 0.4
    by = y_bottom - 0.3
    bw = (x_right - x_left) + 0.8
    bh = (y_top - y_bottom) + 0.6
    n_digits = max(1, component.digits)
    digit_centers, bx, bw = _digit_centers(cx, bx, bw, n_digits, s)

    axes.add_patch(
        Rectangle(
            (bx, by),
            bw,
            bh,
            facecolor=style.color("seven_segment.body"),
            edgecolor=style.color("seven_segment.body_edge"),
            linewidth=style.dim("seven_segment.body_edge_width"),
            zorder=7,
        )
    )

    for dcx in digit_centers:
        _draw_digit(axes, dcx, cy, s, style)

    _seven_segment_pins(axes, geo, component, style)

    common_tag = "CC" if component.common == "cathode" else "CA"
    label_text = f"{component.ref} {common_tag}" if component.ref else common_tag
    axes.text(
        cx,
        by - 0.15,
        label_text,
        ha="center",
        va="top",
        fontsize=8.0,
        fontweight="bold",
        color=style.color("label.ref"),
        zorder=9,
        bbox=style.label_bbox,
    )
