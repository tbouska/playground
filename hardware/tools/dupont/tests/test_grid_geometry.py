"""Contract tests for holes<->mm<->px transform + cross-coord compare (dupont/grid/geometry.py).

These tests pin the geometry contract: converting a hole address to/from pixel
space at the measured Wokwi scale, snapping a pixel point to its nearest hole
within tolerance, and comparing a layout (breadboard) circuit's hole positions
against a Wokwi circuit's pixel positions once co-registered on a shared
anchor component. Values are taken from the PRD contract, not from running an
implementation.
"""

import pytest

from dupont.grid.geometry import (
    GeometryFinding,
    PlacementOutOfTolerance,
    SNAP_TOLERANCE_MM,
    compare_geometry,
    nearest_hole,
    register,
    to_hole,
    to_px,
)
from dupont.grid.holes import PITCH_MM, hole_coords
from dupont.grid.scale import px_per_mm
from dupont.model.entities import Circuit, Component, Pin, Placement


def _pin(instance_id: str) -> Pin:
    return Pin(pin_id=f"{instance_id}.1", name="1", type="passive", physical_index=0)


def _component(instance_id: str) -> Component:
    return Component(instance_id=instance_id, kind="generic", pins=(_pin(instance_id),))


def _layout_circuit(holes: dict[str, str]) -> Circuit:
    """A breadboard circuit with one Placement per component, anchored at a hole."""
    components = tuple(_component(ref) for ref in holes)
    placements = tuple(
        Placement(ref, {"pins": [{"name": "1", "hole": hole}]}, 0.0, "breadboard", "fixture")
        for ref, hole in holes.items()
    )
    return Circuit(title="layout", components=components, nets=(), placements=placements)


def _wokwi_circuit(
    pxs: dict[str, tuple[float, float]], with_marker: bool = True
) -> Circuit:
    """A Wokwi circuit with one px Placement per component, optionally marked as breadboard-origin."""
    components = tuple(_component(ref) for ref in pxs)
    placements = [
        Placement(ref, {"px": px}, 0.0, "wokwi", "fixture") for ref, px in pxs.items()
    ]
    if with_marker:
        placements.append(
            Placement(
                "__wokwi_breadboard__", {"px": (0.0, 0.0)}, 0.0, "wokwi", "wokwi/breadboard-origin"
            )
        )
    return Circuit(title="wokwi", components=components, nets=(), placements=tuple(placements))


def test_snap_tolerance_mm_is_one_millimetre() -> None:
    assert SNAP_TOLERANCE_MM == 1.0


@pytest.mark.parametrize("address", ["B1", "I19", "E37", "T+1", "B-31"])
def test_to_px_computes_col_row_scaled_by_pitch_and_measured_px_per_mm(address: str) -> None:
    col, row = hole_coords(address)
    expected = (col * PITCH_MM * px_per_mm(), row * PITCH_MM * px_per_mm())
    assert to_px(address) == pytest.approx(expected)


@pytest.mark.parametrize("address", ["Z9", "K1", ""])
def test_to_px_invalid_address_raises_value_error(address: str) -> None:
    with pytest.raises(ValueError):
        to_px(address)


@pytest.mark.parametrize("address", ["B1", "I19", "E37", "T+1", "B-31"])
def test_nearest_hole_round_trip_recovers_exact_address_and_zero_distance(address: str) -> None:
    x_px, y_px = to_px(address)
    assert nearest_hole(x_px, y_px) == (address, 0.0)


def test_to_hole_exact_on_hole_returns_that_hole() -> None:
    x_px, y_px = to_px("E37")
    assert to_hole(x_px, y_px) == "E37"


def test_to_hole_within_tolerance_snaps_to_hole() -> None:
    x_px, y_px = to_px("E37")
    displaced_x = x_px + 0.5 * px_per_mm()  # 0.5mm: within tolerance and within half a pitch step
    assert to_hole(displaced_x, y_px) == "E37"
    addr, dist = nearest_hole(displaced_x, y_px)
    assert addr == "E37"
    assert dist == pytest.approx(0.5)


def test_to_hole_just_within_tolerance_boundary_snaps_to_hole() -> None:
    x_px, y_px = to_px("E37")
    # 0.99mm: just inside the 1.0mm tolerance. Asserting a binary snap at the exact
    # 1.0mm knife-edge would depend on float rounding of dist against the `<=` compare,
    # so stay just inside to keep the snap deterministic while still exercising
    # near-boundary behaviour (the 1.2mm test below brackets the beyond-tolerance side).
    displaced_x = x_px + 0.99 * px_per_mm()
    assert to_hole(displaced_x, y_px) == "E37"
    _, dist = nearest_hole(displaced_x, y_px)
    assert dist == pytest.approx(0.99)


def test_to_hole_beyond_tolerance_raises_placement_out_of_tolerance() -> None:
    x_px, y_px = to_px("E37")
    # 1.2mm: beyond the 1.0mm tolerance, but still under half a pitch step (1.27mm) so
    # the nearest hole is still E37 and the reported distance is unambiguous.
    displaced_x = x_px + 1.2 * px_per_mm()
    addr, dist = nearest_hole(displaced_x, y_px)
    assert addr == "E37"
    assert dist == pytest.approx(1.2)
    with pytest.raises(PlacementOutOfTolerance):
        to_hole(displaced_x, y_px)


def test_placement_out_of_tolerance_is_value_error_subclass() -> None:
    assert issubclass(PlacementOutOfTolerance, ValueError)


def test_to_hole_custom_tolerance_widens_acceptance() -> None:
    x_px, y_px = to_px("E37")
    displaced_x = x_px + 1.2 * px_per_mm()  # beyond the 1.0mm default tolerance
    with pytest.raises(PlacementOutOfTolerance):
        to_hole(displaced_x, y_px)
    assert to_hole(displaced_x, y_px, tolerance_mm=2.0) == "E37"


def test_register_computes_offset_between_layout_and_wokwi_anchor() -> None:
    layout = _layout_circuit({"C1": "B1"})
    anchor_px = to_px("B1")
    wokwi_px = (anchor_px[0] + 12.0, anchor_px[1] - 6.0)
    wokwi = _wokwi_circuit({"C1": wokwi_px})

    dx_mm, dy_mm = register(layout, wokwi)

    assert dx_mm == pytest.approx(-12.0 / px_per_mm())
    assert dy_mm == pytest.approx(6.0 / px_per_mm())


def test_register_raises_value_error_when_no_shared_geometry_component() -> None:
    layout = _layout_circuit({"C1": "B1"})
    wokwi = _wokwi_circuit({})  # only the breadboard marker; no shared component geometry

    with pytest.raises(ValueError):
        register(layout, wokwi)


def test_compare_geometry_returns_no_findings_when_aligned() -> None:
    layout = _layout_circuit({"C1": "B1", "C2": "E37"})
    wokwi = _wokwi_circuit({"C1": to_px("B1"), "C2": to_px("E37")})

    assert compare_geometry(layout, wokwi) == []


def test_compare_geometry_flags_drift_beyond_tolerance_on_non_anchor_component() -> None:
    layout = _layout_circuit({"C1": "B1", "C2": "E37"})
    e37_x, e37_y = to_px("E37")
    drifted_px = (e37_x + 1.5 * px_per_mm(), e37_y)  # 1.5mm drift, beyond the 1.0mm tolerance
    wokwi = _wokwi_circuit({"C1": to_px("B1"), "C2": drifted_px})

    findings = compare_geometry(layout, wokwi)

    assert len(findings) == 1
    finding = findings[0]
    assert isinstance(finding, GeometryFinding)
    assert finding.component_ref == "C2"
    assert finding.layout_hole == "E37"
    # The exact snapped wokwi-side hole address is an implementation detail the contract
    # does not pin down (pre- vs post-offset quantization); only that it is populated.
    assert isinstance(finding.wokwi_hole, str) and finding.wokwi_hole
    assert finding.drift_mm == pytest.approx(1.5)
    assert finding.drift_mm > SNAP_TOLERANCE_MM
    assert finding.severity == "warning"


def test_compare_geometry_returns_no_findings_without_wokwi_breadboard_marker() -> None:
    layout = _layout_circuit({"C1": "B1", "C2": "E37"})
    e37_x, e37_y = to_px("E37")
    drifted_px = (e37_x + 1.5 * px_per_mm(), e37_y)
    wokwi = _wokwi_circuit({"C1": to_px("B1"), "C2": drifted_px}, with_marker=False)

    assert compare_geometry(layout, wokwi) == []


def test_compare_geometry_raises_runtime_error_when_scale_not_measured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layout = _layout_circuit({"C1": "B1", "C2": "E37"})
    e37_x, e37_y = to_px("E37")
    drifted_px = (e37_x + 1.5 * px_per_mm(), e37_y)
    wokwi = _wokwi_circuit({"C1": to_px("B1"), "C2": drifted_px})

    # Assumption: geometry.py reads MEASURED as a module attribute (dupont.grid.scale.MEASURED)
    # rather than via a `from ... import MEASURED` binding, per the CONTRACT's guidance.
    monkeypatch.setattr("dupont.grid.scale.MEASURED", False)

    with pytest.raises(RuntimeError):
        compare_geometry(layout, wokwi)
