"""Behavior-lock tests for wire-routing helpers in render_layout.

Covers:
- _hop_polyline: vertex count for 0, 1, and 2 crossings (locks per-crossing step formula).
- _wire_channels / _route: the routing contract -- clean wires stay direct, wires
  whose direct path would clip a part are rerouted to cross nothing, wires render
  above components, and wires sharing a lane fan apart instead of overlaying.
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
# _wire_channels / _route
# ---------------------------------------------------------------------------


def test_clear_wire_is_drawn_direct() -> None:
    """A wire with nothing between its endpoints is the straight two-point segment."""
    geo = r.Geometry(30)
    wire = r.Component(kind="wire", endpoints=("A1", "A10"), color="green")
    routes = r._wire_channels(geo, (wire,))
    assert routes[id(wire)] == [geo.hole("A1"), geo.hole("A10")]


def test_wire_reroutes_around_a_component() -> None:
    """A wire whose direct path would clip a part is rerouted to cross nothing."""
    geo = r.Geometry(30)
    # Module at columns 4-8, no pins -> spans rows A-J across those columns.
    module = r.Component(kind="module", label="MCU", span=(4, 8))
    # Straight A1->E15 clips the module; the router must skirt it entirely.
    wire = r.Component(kind="wire", endpoints=("A1", "E15"), color="blue")

    rects = r._component_rects(geo, (module, wire))
    routes = r._wire_channels(geo, (module, wire))

    # The chosen straight line does hit the module...
    assert r._crossings([geo.hole("A1"), geo.hole("E15")], rects) > 0
    # ...but the routed path is steered clear of every part.
    assert r._crossings(routes[id(wire)], rects) == 0


def test_wires_render_above_components() -> None:
    """Wires sit above every component so a forced crossing lies visibly on top."""
    # Component drawers top out at zorder 9 (module pins / 7-seg).
    assert r._WIRE_ZORDER > 9.0
    assert r._WIRE_DOT_ZORDER >= r._WIRE_ZORDER


def test_shared_lane_wires_fan_apart() -> None:
    """Two wires pushed into the same lane separate instead of overlaying."""
    geo = r.Geometry(40)
    module = r.Component(kind="module", label="MCU", span=(4, 8))
    w1 = r.Component(kind="wire", endpoints=("A1", "E20"), color="red")
    w2 = r.Component(kind="wire", endpoints=("A2", "E22"), color="blue")

    routes = r._wire_channels(geo, (module, w1, w2))
    lane1 = r._path_lane(routes[id(w1)], geo.hole("A1")[1], geo.hole("E20")[1])
    lane2 = r._path_lane(routes[id(w2)], geo.hole("A2")[1], geo.hole("E22")[1])

    assert lane1 is not None and lane2 is not None
    assert lane1 != lane2
