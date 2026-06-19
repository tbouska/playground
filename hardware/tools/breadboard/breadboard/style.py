from typing import Any

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
