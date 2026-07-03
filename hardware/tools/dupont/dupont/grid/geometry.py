"""Geometry transforms and cross-coordinate comparison for dupont + Wokwi.

Provides hole<->pixel conversions at the measured Wokwi scale, snapping of
arbitrary pixel points to the nearest grid hole within tolerance, and
comparison of a layout (breadboard) circuit's hole positions against a
Wokwi circuit's pixel positions once co-registered on a shared anchor.
"""

from dataclasses import dataclass
from math import hypot

from breadboard.geometry import LINE_ORDER

from dupont.grid.holes import PITCH_MM, hole_coords
from dupont.grid import scale
from dupont.grid.scale import px_per_mm
from dupont.model.entities import Circuit


SNAP_TOLERANCE_MM: float = 1.0


class PlacementOutOfTolerance(ValueError):
    """Raised when a pixel point is farther than the snap tolerance from any hole."""


def to_px(address: str) -> tuple[float, float]:
    """Convert a hole address to pixel coordinates (col, row) in px.

    :param address: A hole address such as ``"F12"`` or ``"B-28"``.
    :type address: str
    :returns: ``(x_px, y_px)`` pixel coordinates.
    :rtype: tuple[float, float]
    :raises ValueError: If the address is invalid.
    """
    col, row = hole_coords(address)
    s = PITCH_MM * px_per_mm()
    return (col * s, row * s)


def nearest_hole(x_px: float, y_px: float) -> tuple[str, float]:
    """Find the nearest grid hole to a pixel point.

    :param x_px: X coordinate in pixels.
    :param y_px: Y coordinate in pixels.
    :returns: ``(address, distance_mm)`` where distance is in millimetres.
    :rtype: tuple[str, float]
    """
    s = PITCH_MM * px_per_mm()
    col = round(x_px / s)
    row = round(y_px / s)

    # Clamp col >= 1
    if col < 1:
        col = 1

    # Clamp row into range
    if row < 0:
        row = 0
    if row >= len(LINE_ORDER):
        row = len(LINE_ORDER) - 1

    line = LINE_ORDER[row]

    # If we landed on a blank gap, pick the nearest non-blank line index
    if line == "":
        best_dist = float("inf")
        best_idx = row
        for i, l in enumerate(LINE_ORDER):
            if l:
                d = abs(i - row)
                if d < best_dist:
                    best_dist = d
                    best_idx = i
        row = best_idx
        line = LINE_ORDER[row]

    address = f"{line}{col}"
    hx, hy = to_px(address)
    distance_mm = hypot(x_px - hx, y_px - hy) / px_per_mm()
    return (address, distance_mm)


def to_hole(x_px: float, y_px: float, tolerance_mm: float = SNAP_TOLERANCE_MM) -> str:
    """Snap a pixel point to its nearest hole within tolerance.

    :param x_px: X coordinate in pixels.
    :param y_px: Y coordinate in pixels.
    :param tolerance_mm: Maximum allowed distance in millimetres.
    :type tolerance_mm: float
    :returns: The hole address if within tolerance.
    :rtype: str
    :raises PlacementOutOfTolerance: If the point is farther than tolerance from any hole.
    """
    addr, dist = nearest_hole(x_px, y_px)
    if dist <= tolerance_mm:
        return addr
    raise PlacementOutOfTolerance(
        f"point ({x_px}, {y_px}) is {dist:.2f} mm from nearest hole {addr}, "
        f"exceeds tolerance {tolerance_mm} mm"
    )


@dataclass(frozen=True)
class GeometryFinding:
    """A single geometry comparison finding between layout and Wokwi circuits.

    :ivar component_ref: The component reference (e.g. ``"C2"``).
    :vartype component_ref: str
    :ivar layout_hole: The layout-side hole address.
    :vartype layout_hole: str
    :ivar wokwi_hole: The Wokwi-side nearest-hole address (informational).
    :vartype wokwi_hole: str
    :ivar drift_mm: Continuous mm drift between layout and Wokwi positions.
    :vartype drift_mm: float
    :ivar severity: Always ``"warning"`` in this module.
    :vartype severity: str
    """

    component_ref: str
    layout_hole: str
    wokwi_hole: str
    drift_mm: float
    severity: str


def _find_shared_geometry_components(
    layout: Circuit, wokwi: Circuit
) -> dict[str, tuple[str, tuple[float, float]]]:
    """Find shared geometry-carrying components between layout and Wokwi circuits.

    Returns a dict mapping component_ref to (layout_hole, wokwi_px).
    """
    layout_map: dict[str, str] = {}
    for p in layout.placements:
        ref = p.component_ref
        if ref.startswith("__"):
            continue
        pins = p.coords.get("pins", [])
        if pins and "hole" in pins[0]:
            layout_map[ref] = pins[0]["hole"]

    wokwi_map: dict[str, tuple[float, float]] = {}
    for p in wokwi.placements:
        ref = p.component_ref
        if ref.startswith("__"):
            continue
        if "px" in p.coords:
            wokwi_map[ref] = p.coords["px"]

    shared: dict[str, tuple[str, tuple[float, float]]] = {}
    for ref in layout_map:
        if ref in wokwi_map:
            shared[ref] = (layout_map[ref], wokwi_map[ref])

    return shared


def register(
    layout: "Circuit",
    wokwi: "Circuit",
    shared: dict[str, tuple[str, tuple[float, float]]] | None = None,
) -> tuple[float, float]:
    """Register layout and Wokwi circuits on their shared anchor component.

    The anchor is the shared geometry-carrying component with the
    lexicographically smallest component_ref.

    :param layout: The layout (breadboard) circuit.
    :param wokwi: The Wokwi circuit.
    :param shared: Precomputed shared-geometry map (from
        ``_find_shared_geometry_components``); recomputed when ``None``. Lets a
        caller that already scanned avoid a second pass.
    :returns: ``(dx_mm, dy_mm)`` offset = layout_mm - wokwi_mm.
    :rtype: tuple[float, float]
    :raises ValueError: If there is no shared geometry-carrying component.
    """
    if shared is None:
        shared = _find_shared_geometry_components(layout, wokwi)
    if not shared:
        raise ValueError("no shared geometry-carrying component found")

    anchor_ref = min(shared)
    anchor_hole, anchor_px = shared[anchor_ref]

    col, row = hole_coords(anchor_hole)
    layout_anchor_mm = (col * PITCH_MM, row * PITCH_MM)
    wokwi_anchor_mm = (anchor_px[0] / px_per_mm(), anchor_px[1] / px_per_mm())

    return (layout_anchor_mm[0] - wokwi_anchor_mm[0], layout_anchor_mm[1] - wokwi_anchor_mm[1])


def compare_geometry(
    layout: Circuit, wokwi: Circuit
) -> list[GeometryFinding]:
    """Compare layout and Wokwi circuit geometries after co-registration.

    :param layout: The layout (breadboard) circuit.
    :param wokwi: The Wokwi circuit.
    :returns: List of GeometryFinding for components exceeding tolerance.
    :rtype: list[GeometryFinding]
    :raises RuntimeError: If the scale has not been measured.
    """
    # Check for wokwi breadboard marker first
    has_marker = any(
        p.component_ref == "__wokwi_breadboard__" for p in wokwi.placements
    )
    if not has_marker:
        return []

    # Check MEASURED dynamically
    if not scale.MEASURED:
        raise RuntimeError("geometry comparison requires measured scale (scale.MEASURED is False)")

    # Marker-carrying but no component shares geometry with the layout: the
    # diagram is connectivity-only, not a drift error. Scan once and reuse it
    # for registration (no second pass).
    shared = _find_shared_geometry_components(layout, wokwi)
    if not shared:
        return []
    offset = register(layout, wokwi, shared)
    anchor_ref = min(shared)

    findings: list[GeometryFinding] = []
    for ref in shared:
        if ref == anchor_ref:
            continue

        layout_hole, wokwi_px = shared[ref]
        col, row = hole_coords(layout_hole)
        layout_mm = (col * PITCH_MM, row * PITCH_MM)

        wokwi_mm = (wokwi_px[0] / px_per_mm() + offset[0], wokwi_px[1] / px_per_mm() + offset[1])

        drift_mm = hypot(wokwi_mm[0] - layout_mm[0], wokwi_mm[1] - layout_mm[1])

        if drift_mm > SNAP_TOLERANCE_MM:
            corrected_px = (wokwi_mm[0] * px_per_mm(), wokwi_mm[1] * px_per_mm())
            wokwi_hole, _ = nearest_hole(corrected_px[0], corrected_px[1])
            findings.append(
                GeometryFinding(
                    component_ref=ref,
                    layout_hole=layout_hole,
                    wokwi_hole=wokwi_hole,
                    drift_mm=drift_mm,
                    severity="warning",
                )
            )

    findings.sort(key=lambda f: f.component_ref)
    return findings
