"""Behavior-lock tests for wire-routing helpers in render_layout.

Covers:
- _hop_polyline: vertex count for 0, 1, and 2 crossings (locks per-crossing step formula).
- _wire_channels: lane assignment for clear path, blocked path, nested wires, and
  same-row/same-column wires (no lane).
"""

import breadboard.wires as r


# ---------------------------------------------------------------------------
# _hop_polyline
# ---------------------------------------------------------------------------


def test_hop_polyline_no_crossing_is_straight_segment() -> None:
    """Zero crossings returns exactly the two endpoints, nothing inserted."""
    xs, ys = r._hop_polyline(1.0, 5.0, -7.0, [], 0.22)
    assert len(xs) == 2
    assert len(ys) == 2
    assert xs == [1.0, 5.0]
    assert ys == [-7.0, -7.0]


def test_hop_polyline_adds_steps_plus_one_vertices_per_crossing() -> None:
    """Each crossing inserts steps+1 vertices (default steps=8 -> 9 per crossing).

    Formula: total = 2 (endpoints) + N * (steps + 1).
    Verified by running the function with 0, 1, and 2 crossings.
    """
    xs1, ys1 = r._hop_polyline(1.0, 5.0, -7.0, [3.0], 0.22)
    assert len(xs1) == 11  # 2 + 1*9
    assert len(ys1) == 11

    xs2, ys2 = r._hop_polyline(1.0, 5.0, -7.0, [2.0, 4.0], 0.22)
    assert len(xs2) == 20  # 2 + 2*9
    assert len(ys2) == 20


# ---------------------------------------------------------------------------
# _wire_channels
# ---------------------------------------------------------------------------


def test_wire_channels_clear_path_gets_centre_gap_lane() -> None:
    """A diagonal wire with no blocks in its path gets the E/F midpoint lane."""
    geo = r.Geometry(30)
    gap_y = (geo.line_y["E"] + geo.line_y["F"]) / 2.0  # -8.0

    wire = r.Component(kind="wire", endpoints=("A1", "E10"), color="red")
    channels = r._wire_channels(geo, (wire,))

    assert channels[id(wire)] == gap_y


def test_wire_channels_falls_back_to_below_bank_lane_when_centre_blocked() -> None:
    """A diagonal wire that would clip a block routes via the J/B+ midpoint instead."""
    geo = r.Geometry(30)
    below_y = (geo.line_y["J"] + geo.line_y["B+"]) / 2.0  # -14.0

    # Module at columns 4-8, no pins -> spans all A-J rows, obstructs the centre gap.
    module = r.Component(kind="module", label="MCU", span=(4, 8))
    # Wire from A1 to E15: horizontal run at gap_y crosses the module block.
    wire = r.Component(kind="wire", endpoints=("A1", "E15"), color="blue")

    channels = r._wire_channels(geo, (module, wire))

    assert channels[id(wire)] == below_y


def test_wire_channels_wider_span_gets_outer_lane() -> None:
    """When two diagonal wires share a base lane, the wider span sits further out.

    Both wires here are clear of blocks so they share gap_y=-8.0 as their base.
    With two members the lanes are base ± 0.25 (step=0.5, offsets -0.25 and +0.25).
    The wider wire (15-col span) receives the more-negative y (-8.25); the
    narrower wire (5-col span) receives the less-negative y (-7.75).
    """
    geo = r.Geometry(30)

    wire_wide = r.Component(kind="wire", endpoints=("A1", "E16"), color="red")
    wire_narrow = r.Component(kind="wire", endpoints=("A5", "E10"), color="blue")
    channels = r._wire_channels(geo, (wire_wide, wire_narrow))

    assert channels[id(wire_wide)] == -8.25
    assert channels[id(wire_narrow)] == -7.75
    # Wider span is further from the board centre (more negative).
    assert channels[id(wire_wide)] < channels[id(wire_narrow)]


def test_wire_channels_same_row_wire_gets_no_lane() -> None:
    """A wire whose endpoints share a row is straight and receives no lane entry."""
    geo = r.Geometry(30)
    wire = r.Component(kind="wire", endpoints=("A1", "A10"), color="green")
    channels = r._wire_channels(geo, (wire,))
    assert id(wire) not in channels


def test_wire_channels_same_column_wire_gets_no_lane() -> None:
    """A wire whose endpoints share a column is straight and receives no lane entry."""
    geo = r.Geometry(30)
    wire = r.Component(kind="wire", endpoints=("A5", "E5"), color="yellow")
    channels = r._wire_channels(geo, (wire,))
    assert id(wire) not in channels
