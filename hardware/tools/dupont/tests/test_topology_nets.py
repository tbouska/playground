"""Contract tests for breadboard net extraction (dupont/topology/nets.py).

Pins the ``extract_nets`` union-find contract over the 10 canonical breadboard
node patterns, plus the ``component_pins`` geometry-native pin mapping. Every
test is black-box: expected values are derived by applying the published
contract to a tiny inline Layout, never by running an implementation. The
already-implemented ``node_key`` (dupont.grid.holes) is the oracle for which
holes collapse to a shared base node.
"""

import pytest

from breadboard.model import Component, Layout, Pin
from dupont.model.entities import Net, PinRef
from dupont.topology.nets import component_pins, extract_nets


def _layout(*components: Component) -> Layout:
    return Layout(title="t", columns=63, components=tuple(components))


def _members(net: Net) -> set[tuple[str, str]]:
    return {(ref.instance_id, ref.pin) for ref in net.member_pin_refs}


def _net_of(nets: tuple[Net, ...], instance_id: str, pin: str) -> Net:
    matches = [n for n in nets if (instance_id, pin) in _members(n)]
    assert len(matches) == 1, (
        f"expected exactly one net containing {(instance_id, pin)}, got {len(matches)}"
    )
    return matches[0]


# --------------------------------------------------------------------------- #
# The 10 canonical node patterns.
# --------------------------------------------------------------------------- #


def test_column_merge_within_bank_is_one_net() -> None:
    # G29 and F29 are both lower-bank column 29 -> one shared node.
    layout = _layout(
        Component(kind="resistor", ref="R1", legs=("G29", "G34")),
        Component(kind="resistor", ref="R2", legs=("F29", "F34")),
    )
    assert extract_nets(layout) == (
        Net(
            "bb_net1",
            (PinRef("R1", "1"), PinRef("R2", "1")),
            "breadboard/column-merge col29",
        ),
        Net(
            "bb_net2",
            (PinRef("R1", "2"), PinRef("R2", "2")),
            "breadboard/column-merge col34",
        ),
    )


def test_bank_gap_separates_upper_and_lower_into_two_nets() -> None:
    # E5 (upper) and F5 (lower) are DISTINCT nodes despite the shared column.
    layout = _layout(
        Component(kind="module", ref="U1", pins=(Pin("P", "E5"),)),
        Component(kind="module", ref="U2", pins=(Pin("P", "F5"),)),
    )
    nets = extract_nets(layout)
    assert nets == (
        Net("bb_net1", (PinRef("U2", "P"),), "breadboard/column-merge col5"),
        Net("bb_net2", (PinRef("U1", "P"),), "breadboard/column-merge col5"),
    )
    assert _net_of(nets, "U1", "P").net_id != _net_of(nets, "U2", "P").net_id


def test_continuous_power_rail_merges_pins_on_same_line() -> None:
    # B-5 and B-20 are the same rail line -> one node.
    layout = _layout(
        Component(kind="module", ref="U1", pins=(Pin("VCC", "B-5"),)),
        Component(kind="module", ref="U2", pins=(Pin("VCC", "B-20"),)),
    )
    assert extract_nets(layout) == (
        Net(
            "bb_net1",
            (PinRef("U1", "VCC"), PinRef("U2", "VCC")),
            "breadboard/rail B-",
        ),
    )


def test_jumper_bridges_two_grid_columns_into_one_net() -> None:
    # A wire unions lower-col5 and lower-col20; each seats a pin -> one net.
    layout = _layout(
        Component(kind="wire", color="green", endpoints=("G5", "G20")),
        Component(kind="module", ref="U1", pins=(Pin("A", "G5"),)),
        Component(kind="module", ref="U2", pins=(Pin("A", "G20"),)),
    )
    assert extract_nets(layout) == (
        Net(
            "bb_net1",
            (PinRef("U1", "A"), PinRef("U2", "A")),
            "breadboard/jumper G20-G5",  # endpoints sorted as plain strings
        ),
    )


def test_multi_leg_part_does_not_union_its_own_legs() -> None:
    # R1 spans lower-col10 and lower-col14 but does NOT merge them; it bridges.
    layout = _layout(
        Component(kind="resistor", ref="R1", legs=("G10", "G14")),
        Component(kind="module", ref="U1", pins=(Pin("P", "G10"),)),
        Component(kind="module", ref="U2", pins=(Pin("P", "G14"),)),
    )
    nets = extract_nets(layout)
    assert nets == (
        Net(
            "bb_net1",
            (PinRef("R1", "1"), PinRef("U1", "P")),
            "breadboard/column-merge col10",
        ),
        Net(
            "bb_net2",
            (PinRef("R1", "2"), PinRef("U2", "P")),
            "breadboard/column-merge col14",
        ),
    )
    assert _net_of(nets, "R1", "1").net_id != _net_of(nets, "R1", "2").net_id


def test_two_components_sharing_a_node_form_one_net() -> None:
    # R1 leg G8 and D1 leg F8 both land on lower-col8 -> one shared net.
    layout = _layout(
        Component(kind="resistor", ref="R1", legs=("G8", "G30")),
        Component(kind="led", ref="D1", legs=("F8", "F30")),
    )
    nets = extract_nets(layout)
    assert nets == (
        Net(
            "bb_net1",
            (PinRef("D1", "1"), PinRef("R1", "1")),
            "breadboard/column-merge col8",
        ),
        Net(
            "bb_net2",
            (PinRef("D1", "2"), PinRef("R1", "2")),
            "breadboard/column-merge col30",
        ),
    )
    assert _net_of(nets, "R1", "1").net_id == _net_of(nets, "D1", "1").net_id


def test_rail_to_rail_jumper_merges_two_rail_lines() -> None:
    # A wire unions T+ and B+ rail lines; wire-join wins over rail provenance.
    layout = _layout(
        Component(kind="wire", color="red", endpoints=("T+5", "B+10")),
        Component(kind="module", ref="U1", pins=(Pin("VCC", "T+5"),)),
        Component(kind="module", ref="U2", pins=(Pin("VCC", "B+10"),)),
    )
    assert extract_nets(layout) == (
        Net(
            "bb_net1",
            (PinRef("U1", "VCC"), PinRef("U2", "VCC")),
            "breadboard/jumper B+10-T+5",  # sorted as plain strings
        ),
    )


def test_adjacent_jumpers_stay_distinct() -> None:
    # Two independent wires in adjacent columns must NOT merge into one net.
    layout = _layout(
        Component(kind="wire", color="green", endpoints=("G5", "G6")),
        Component(kind="wire", color="green", endpoints=("G7", "G8")),
        Component(kind="module", ref="U1", pins=(Pin("P", "G5"),)),
        Component(kind="module", ref="U2", pins=(Pin("P", "G6"),)),
        Component(kind="module", ref="U3", pins=(Pin("P", "G7"),)),
        Component(kind="module", ref="U4", pins=(Pin("P", "G8"),)),
    )
    nets = extract_nets(layout)
    assert nets == (
        Net(
            "bb_net1",
            (PinRef("U1", "P"), PinRef("U2", "P")),
            "breadboard/jumper G5-G6",
        ),
        Net(
            "bb_net2",
            (PinRef("U3", "P"), PinRef("U4", "P")),
            "breadboard/jumper G7-G8",
        ),
    )
    assert _net_of(nets, "U1", "P").net_id != _net_of(nets, "U3", "P").net_id


def test_wire_joining_empty_nodes_yields_no_net() -> None:
    # The wire bridges two holes that carry no pin -> dangling -> no net emitted
    # for it. Only U1's pin-bearing node produces a net.
    layout = _layout(
        Component(kind="wire", color="green", endpoints=("G5", "G20")),
        Component(kind="module", ref="U1", pins=(Pin("P", "J1"),)),
    )
    nets = extract_nets(layout)
    assert nets == (
        Net("bb_net1", (PinRef("U1", "P"),), "breadboard/column-merge col1"),
    )
    assert all(not n.provenance.startswith("breadboard/jumper") for n in nets)


def test_same_bank_different_columns_do_not_merge() -> None:
    # Two pins in the same bank but different columns, no wire -> two nets.
    layout = _layout(
        Component(kind="module", ref="U1", pins=(Pin("P", "G8"),)),
        Component(kind="module", ref="U2", pins=(Pin("P", "G12"),)),
    )
    nets = extract_nets(layout)
    assert nets == (
        Net("bb_net1", (PinRef("U1", "P"),), "breadboard/column-merge col8"),
        Net("bb_net2", (PinRef("U2", "P"),), "breadboard/column-merge col12"),
    )
    assert _net_of(nets, "U1", "P").net_id != _net_of(nets, "U2", "P").net_id


def test_net_ids_number_by_ascending_min_node_key() -> None:
    # Ordering oracle: lower < upper within a bank tuple, and every bank node
    # sorts before every rail node. So the col-3 lower net precedes the col-1
    # upper net, which precedes the rail net.
    layout = _layout(
        Component(kind="module", ref="U1", pins=(Pin("P", "G3"),)),  # bank lower 3
        Component(kind="module", ref="U2", pins=(Pin("P", "A1"),)),  # bank upper 1
        Component(kind="module", ref="U3", pins=(Pin("P", "T+7"),)),  # rail T+
    )
    nets = extract_nets(layout)
    assert tuple(n.net_id for n in nets) == ("bb_net1", "bb_net2", "bb_net3")
    assert nets == (
        Net("bb_net1", (PinRef("U1", "P"),), "breadboard/column-merge col3"),
        Net("bb_net2", (PinRef("U2", "P"),), "breadboard/column-merge col1"),
        Net("bb_net3", (PinRef("U3", "P"),), "breadboard/rail T+"),
    )


# --------------------------------------------------------------------------- #
# component_pins: geometry-native (pin_name, hole) pairs per component kind.
# --------------------------------------------------------------------------- #


def test_component_pins_resistor_uses_1_indexed_list_legs() -> None:
    c = Component(kind="resistor", ref="R1", value="220", legs=("G25", "G29"))
    assert component_pins(c) == [("1", "G25"), ("2", "G29")]


def test_component_pins_plain_led_is_list_form_pins_1_and_2() -> None:
    c = Component(kind="led", ref="D1", legs=("F29", "F30"))
    assert component_pins(c) == [("1", "F29"), ("2", "F30")]


def test_component_pins_dict_legs_use_named_legs() -> None:
    c = Component(
        kind="led-rgb",
        ref="D2",
        named_legs={"red": "A1", "green": "A2", "blue": "A3"},
    )
    assert component_pins(c) == [("red", "A1"), ("green", "A2"), ("blue", "A3")]


def test_component_pins_module_uses_pin_name_and_hole() -> None:
    c = Component(
        kind="module", ref="U1", pins=(Pin("GPIO2", "I5"), Pin("GND", "I19"))
    )
    assert component_pins(c) == [("GPIO2", "I5"), ("GND", "I19")]


def test_component_pins_wire_has_no_pins() -> None:
    c = Component(kind="wire", color="green", endpoints=("J5", "F25"))
    assert component_pins(c) == []


def test_component_pins_power_has_no_pins() -> None:
    c = Component(kind="power")
    assert component_pins(c) == []


def test_component_pins_unmappable_kind_raises_value_error() -> None:
    with pytest.raises(ValueError):
        component_pins(Component(kind="banana"))
