import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

from breadboard.geometry import Geometry
from breadboard.style import (
    BOARD_COLOR,
    BOARD_EDGE,
    GAP_COLOR,
    GAP_SHADOW,
    HIGHLIGHT_COLOR,
    HOLE_EDGE,
    HOLE_FILL,
    HOLE_HILITE,
    HOLE_RADIUS,
    HOLE_SHADOW,
    RAIL_MINUS_COLOR,
    RAIL_PLUS_COLOR,
    SHADOW_COLOR,
)


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
