"""Tests for dupont.check.connectivity.check_connectivity.

Verifies the schematic<->breadboard net-comparison contract: components
matched by instance_id, nets reduced to membership groups (single-member nets
dropped from both sides before comparison), value normalization on component
value, and deterministic Finding ordering. All tests are black-box: they
assert the published contract, not any implementation detail.
"""

import dataclasses
from pathlib import Path

import pytest

from dupont.check.connectivity import Finding, check_connectivity
from dupont.formats.breadboard.importer import import_layout
from dupont.formats.circuit.importer import import_circuit
from dupont.model.entities import Circuit, Component, Net, Pin, PinRef

# ---------------------------------------------------------------------------
# Fixture paths (relative to the hardware/ root, three levels above this file)
# ---------------------------------------------------------------------------

_HW = Path(__file__).resolve().parents[3]
_HELLO_CIRCUIT = _HW / "arduino-ide-sketchbook/espx/espx-1-1-2-hello-world/circuit.yaml"
_HELLO_LAYOUT = _HW / "arduino-ide-sketchbook/espx/espx-1-1-2-hello-world/layout.yaml"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _findings_by_kind(findings, kind):
    return [f for f in findings if f.kind == kind]


def _mcu(instance_id="U1", extra_pins=()):
    pins = (Pin("GPIO2", "GPIO2", "gpio", 0), Pin("GND", "GND", "power", 1)) + extra_pins
    return Component(instance_id, "mcu", pins)


def _res(instance_id="R1", value="220"):
    pins = (Pin("1", "1", "passive", 0), Pin("2", "2", "passive", 1))
    return Component(instance_id, "resistor", pins, value=value)


def _led(instance_id="D1"):
    pins = (Pin("anode", "anode", "passive", 0), Pin("cathode", "cathode", "passive", 1))
    return Component(instance_id, "led", pins)


def _net(net_id, *refs, prov="test"):
    return Net(net_id, tuple(PinRef(i, p) for i, p in refs), prov)


def _circuit(components, nets, title="t"):
    return Circuit(title, tuple(components), tuple(nets))


def _base_pair():
    """A minimal schematic/breadboard pair that is fully equivalent."""
    components = [_mcu(), _res(), _led()]
    nets = [
        _net("n1", ("U1", "GPIO2"), ("R1", "1")),
        _net("n2", ("R1", "2"), ("D1", "anode")),
        _net("n3", ("U1", "GND"), ("D1", "cathode")),
    ]
    schematic = _circuit(components, nets, title="schematic")
    breadboard = _circuit(components, nets, title="breadboard")
    return schematic, breadboard


# ---------------------------------------------------------------------------
# 1. Happy path: real dual-format oracle
# ---------------------------------------------------------------------------


def test_equivalent_real_circuits_produce_no_findings():
    schematic = import_circuit(_HELLO_CIRCUIT)
    breadboard = import_layout(_HELLO_LAYOUT)
    assert check_connectivity(schematic, breadboard) == []


# ---------------------------------------------------------------------------
# 2. Single-member nets dropped from both sides
# ---------------------------------------------------------------------------


def test_extra_single_member_net_on_one_side_causes_no_net_mismatch():
    schematic, breadboard = _base_pair()
    # Breadboard side carries an extra lone-pin net (e.g. a VIN stub) absent
    # from the schematic side entirely.
    breadboard = dataclasses.replace(
        breadboard,
        nets=breadboard.nets + (_net("n_vin", ("U1", "GPIO2")),),
    )
    findings = check_connectivity(schematic, breadboard)
    assert _findings_by_kind(findings, "net_mismatch") == []


# ---------------------------------------------------------------------------
# 3. Value normalization: "220" == "220Ω"
# ---------------------------------------------------------------------------


def test_value_normalization_absorbs_ohm_suffix_and_whitespace():
    schematic, breadboard = _base_pair()
    schematic = dataclasses.replace(
        schematic,
        components=tuple(
            _res(value="  220Ω") if c.instance_id == "R1" else c for c in schematic.components
        ),
    )
    breadboard = dataclasses.replace(
        breadboard,
        components=tuple(
            _res(value="220") if c.instance_id == "R1" else c for c in breadboard.components
        ),
    )
    findings = check_connectivity(schematic, breadboard)
    assert _findings_by_kind(findings, "value_mismatch") == []


# ---------------------------------------------------------------------------
# 4. value_mismatch (warning)
# ---------------------------------------------------------------------------


def test_differing_component_value_flags_value_mismatch_warning():
    schematic, breadboard = _base_pair()
    schematic = dataclasses.replace(
        schematic,
        components=tuple(
            _res(value="220") if c.instance_id == "R1" else c for c in schematic.components
        ),
    )
    breadboard = dataclasses.replace(
        breadboard,
        components=tuple(
            _res(value="330") if c.instance_id == "R1" else c for c in breadboard.components
        ),
    )
    findings = check_connectivity(schematic, breadboard)
    assert len(findings) == 1
    assert findings[0].kind == "value_mismatch"
    assert findings[0].severity == "warning"
    assert findings[0].entity == "R1"


# ---------------------------------------------------------------------------
# 5. missing_component (error)
# ---------------------------------------------------------------------------


def test_component_absent_from_breadboard_flags_missing_component_error():
    schematic, breadboard = _base_pair()
    breadboard = dataclasses.replace(
        breadboard,
        components=tuple(c for c in breadboard.components if c.instance_id != "D1"),
        nets=tuple(n for n in breadboard.nets if "D1" not in {r.instance_id for r in n.member_pin_refs}),
    )
    findings = check_connectivity(schematic, breadboard)
    missing = _findings_by_kind(findings, "missing_component")
    assert len(missing) == 1
    assert missing[0].severity == "error"
    assert missing[0].entity == "D1"


# ---------------------------------------------------------------------------
# 6. extra_component (error)
# ---------------------------------------------------------------------------


def test_component_only_on_breadboard_flags_extra_component_error():
    schematic, breadboard = _base_pair()
    schematic = dataclasses.replace(
        schematic,
        components=tuple(c for c in schematic.components if c.instance_id != "D1"),
        nets=tuple(n for n in schematic.nets if "D1" not in {r.instance_id for r in n.member_pin_refs}),
    )
    findings = check_connectivity(schematic, breadboard)
    extra = _findings_by_kind(findings, "extra_component")
    assert len(extra) == 1
    assert extra[0].severity == "error"
    assert extra[0].entity == "D1"


# ---------------------------------------------------------------------------
# 7. net_mismatch (error) — injected re-wiring
# ---------------------------------------------------------------------------


def test_moving_a_pin_to_a_different_net_flags_net_mismatch_error():
    schematic, breadboard = _base_pair()
    # On the breadboard side, LED anode is wired directly to GND instead of
    # to the resistor: this changes the >=2-member membership partition
    # without changing which components exist.
    breadboard = dataclasses.replace(
        breadboard,
        nets=(
            _net("n1", ("U1", "GPIO2"), ("R1", "1")),
            _net("n2", ("R1", "2")),
            _net("n3", ("U1", "GND"), ("D1", "cathode"), ("D1", "anode")),
        ),
    )
    findings = check_connectivity(schematic, breadboard)
    mismatches = _findings_by_kind(findings, "net_mismatch")
    assert len(mismatches) >= 1
    finding = mismatches[0]
    assert finding.severity == "error"
    combined = finding.schematic_value + finding.breadboard_value
    assert "D1" in combined and "anode" in combined


# ---------------------------------------------------------------------------
# 8. uncanonical_component (error)
# ---------------------------------------------------------------------------


def test_net_referencing_unknown_component_flags_uncanonical_component_error():
    schematic, breadboard = _base_pair()
    # A net on the breadboard side references "X9", an instance_id present in
    # neither side's component list — a part that failed to canonicalize.
    breadboard = dataclasses.replace(
        breadboard,
        nets=breadboard.nets + (_net("n_stray", ("X9", "1"), ("U1", "GPIO2")),),
    )
    findings = check_connectivity(schematic, breadboard)
    uncanonical = _findings_by_kind(findings, "uncanonical_component")
    assert len(uncanonical) >= 1
    assert all(f.severity == "error" for f in uncanonical)


# ---------------------------------------------------------------------------
# 9. Deterministic ordering
# ---------------------------------------------------------------------------


def test_findings_are_sorted_by_kind_then_entity():
    schematic, breadboard = _base_pair()
    # Combine a value_mismatch (R1) with a missing_component (D1) to get two
    # distinct finding kinds in one comparison.
    schematic = dataclasses.replace(
        schematic,
        components=tuple(
            _res(value="220") if c.instance_id == "R1" else c for c in schematic.components
        ),
    )
    breadboard = dataclasses.replace(
        breadboard,
        components=tuple(
            _res(value="330") if c.instance_id == "R1" else c
            for c in breadboard.components
            if c.instance_id != "D1"
        ),
        nets=tuple(
            n for n in breadboard.nets if "D1" not in {r.instance_id for r in n.member_pin_refs}
        ),
    )
    findings = check_connectivity(schematic, breadboard)
    assert len(findings) >= 2
    assert findings == sorted(findings, key=lambda f: (f.kind, f.entity))


# ---------------------------------------------------------------------------
# 10. Finding dataclass shape
# ---------------------------------------------------------------------------


def test_finding_is_frozen_dataclass_with_exact_seven_fields():
    finding = Finding(
        severity="error",
        kind="missing_component",
        entity="R1",
        schematic_value="present",
        breadboard_value="absent",
        schematic_provenance="circuit.yaml",
        breadboard_provenance="layout.yaml",
    )
    assert dataclasses.is_dataclass(finding)
    field_names = {f.name for f in dataclasses.fields(finding)}
    assert field_names == {
        "severity",
        "kind",
        "entity",
        "schematic_value",
        "breadboard_value",
        "schematic_provenance",
        "breadboard_provenance",
    }
    with pytest.raises(dataclasses.FrozenInstanceError):
        finding.severity = "warning"
