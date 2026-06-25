import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

from breadboard.geometry import Geometry
from breadboard.style import Style


def _draw_board_bevel(
    axes: plt.Axes, board_x: float, board_y: float, board_w: float, board_h: float, style: Style
) -> None:
    """Draw the bevelled inner lip: a light edge inset from the rim reads as a raised face."""
    axes.add_patch(
        FancyBboxPatch(
            (board_x + 0.16, board_y + 0.16),
            board_w - 0.32,
            board_h - 0.32,
            boxstyle="round,pad=0,rounding_size=0.7",
            mutation_aspect=1.0,
            facecolor="none",
            edgecolor=style.color("board.highlight"),
            linewidth=style.dim("board.bevel_width"),
            alpha=0.6,
            zorder=0.2,
        )
    )


def _draw_board_frame(
    axes: plt.Axes,
    board_x: float,
    board_y: float,
    board_w: float,
    board_h: float,
    box: str,
    style: Style,
) -> None:
    """Draw the drop shadow, board fill, and bevelled inner lip."""
    # Drop shadow lifts the board off the page; kept small so it stays clear
    # of the row/column legend printed just outside the board.
    axes.add_patch(
        FancyBboxPatch(
            (board_x + 0.12, board_y - 0.14),
            board_w,
            board_h,
            boxstyle=box,
            mutation_aspect=1.0,
            facecolor=style.color("board.shadow"),
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
            facecolor=style.color("board.fill"),
            edgecolor=style.color("board.edge"),
            linewidth=style.dim("board.edge_width"),
            zorder=0,
        )
    )
    _draw_board_bevel(axes, board_x, board_y, board_w, board_h, style)


def _draw_center_channel(
    axes: plt.Axes, geo: Geometry, board_x: float, board_w: float, style: Style
) -> None:
    """Draw the recessed centre channel between rows E and F."""
    mid = (geo.line_y["E"] + geo.line_y["F"]) / 2.0
    chan_half = 0.55
    axes.add_patch(
        Rectangle(
            (board_x, mid - chan_half),
            board_w,
            2 * chan_half,
            facecolor=style.color("gap.fill"),
            edgecolor="none",
            zorder=0.5,
        )
    )
    axes.plot(
        [board_x, board_x + board_w],
        [mid + chan_half, mid + chan_half],
        color=style.color("gap.shadow"),
        linewidth=style.dim("board.gap_line_width"),
        zorder=0.6,
    )
    axes.plot(
        [board_x, board_x + board_w],
        [mid - chan_half, mid - chan_half],
        color=style.color("board.highlight"),
        linewidth=style.dim("board.gap_line_width"),
        alpha=0.7,
        zorder=0.6,
    )


def _draw_board_base(axes: plt.Axes, geo: Geometry, style: Style) -> None:
    """Draw the board substrate (shadow, board, bevel, channel)."""
    ys = list(geo.line_y.values())
    top, bottom = max(ys), min(ys)
    board_x, board_y = 0.2, bottom - 0.8
    board_w, board_h = geo.columns + 0.6, (top - bottom) + 1.6
    box = "round,pad=0,rounding_size=0.35"
    _draw_board_frame(axes, board_x, board_y, board_w, board_h, box, style)
    # Recessed centre channel: a groove *between* rows E and F, clear of holes.
    _draw_center_channel(axes, geo, board_x, board_w, style)


def _draw_socket(
    axes: plt.Axes, col: int, y: float, side: float, off: float, style: Style
) -> None:
    """Draw the bevelled socket hole triple (shadow, hilite, fill) at (col, y)."""
    # Bevelled socket lit from the top-left: the near (top-left) lip throws a
    # shadow down into the recess while the far (bottom-right) wall catches the
    # light, so a faint shadow peeks out top-left and a faint highlight
    # bottom-right of the centred face, reading as a hole pressed into the board.
    axes.add_patch(
        Rectangle(
            (col - side / 2 - off, y - side / 2 + off),
            side,
            side,
            facecolor=style.color("hole.shadow"),
            edgecolor="none",
            zorder=1.88,
        )
    )
    axes.add_patch(
        Rectangle(
            (col - side / 2 + off, y - side / 2 - off),
            side,
            side,
            facecolor=style.color("hole.hilite"),
            edgecolor="none",
            zorder=1.9,
        )
    )
    axes.add_patch(
        Rectangle(
            (col - side / 2, y - side / 2),
            side,
            side,
            facecolor=style.color("hole.fill"),
            edgecolor=style.color("hole.edge"),
            linewidth=style.dim("hole.edge_width"),
            zorder=2,
        )
    )


def _draw_rails_and_holes(axes: plt.Axes, geo: Geometry, style: Style) -> None:
    """Draw the power rails, socket holes, and left/right tick labels."""
    for key, y in geo.line_y.items():
        if key in ("T+", "B+"):
            axes.plot(
                [1, geo.columns],
                [y, y],
                color=style.color("rail.plus"),
                linewidth=style.dim("rail.width"),
                zorder=1,
            )
        if key in ("T-", "B-"):
            axes.plot(
                [1, geo.columns],
                [y, y],
                color=style.color("rail.minus"),
                linewidth=style.dim("rail.width"),
                zorder=1,
            )
        side = style.dim("hole.radius") * 1.7
        off = side * 0.1
        for col in range(1, geo.columns + 1):
            _draw_socket(axes, col, y, side, off, style)
        label = key
        if key in ("T+", "B+"):
            label = "+"
        elif key in ("T-", "B-"):
            label = "-"
        axes.text(
            0.0,
            y,
            label,
            ha="right",
            va="center",
            fontsize=8,
            color=style.color("tick_label.color"),
        )
        axes.text(
            geo.columns + 1.0,
            y,
            label,
            ha="left",
            va="center",
            fontsize=8,
            color=style.color("tick_label.color"),
        )


def _draw_column_labels(axes: plt.Axes, geo: Geometry, style: Style, top: float, bottom: float) -> None:
    """Draw the numbered column labels above and below the board."""
    for col in range(1, geo.columns + 1):
        if col == 1 or col % 5 == 0:
            axes.text(
                col,
                top + 1.05,
                str(col),
                ha="center",
                va="bottom",
                fontsize=7,
                color=style.color("column_label.color"),
            )
            axes.text(
                col,
                bottom - 1.05,
                str(col),
                ha="center",
                va="top",
                fontsize=7,
                color=style.color("column_label.color"),
            )


def _draw_board(axes: plt.Axes, geo: Geometry, style: Style) -> None:
    """Draw the board background, rails, holes, and row/column labels."""
    ys = list(geo.line_y.values())
    top, bottom = max(ys), min(ys)
    _draw_board_base(axes, geo, style)
    _draw_rails_and_holes(axes, geo, style)
    _draw_column_labels(axes, geo, style, top, bottom)
