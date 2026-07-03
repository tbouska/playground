"""Tests for dupont.check.geometry: check_three_format, Finding3, format_three_report.

Written from the contract BEFORE the implementation exists (TDD red state).
All tests are black-box: they assert on the returned Finding3 list, format_three_report
records/summary, and (in test_cli_check.py) the CLI rc/output. Never on internals.
"""

from __future__ import annotations

import copy
import re
from pathlib import Path

from dupont.check.geometry import Finding3, check_three_format, format_three_report
from dupont.formats.breadboard.importer import import_layout
from dupont.formats.circuit.importer import import_circuit
from dupont.formats.wokwi.importer import import_wokwi
from dupont.grid.geometry import to_px
from dupont.grid.scale import px_per_mm
from dupont.model.entities import Circuit, Component, Net, Pin, PinRef, Placement

# ---------------------------------------------------------------------------
# Fixture path (relative to the hardware/ root, three levels above this file)
# ---------------------------------------------------------------------------

_HW = Path(__file__).resolve().parents[3]
_ESPX = _HW / "arduino-ide-sketchbook" / "espx" / "espx-1-1-2-hello-world"

# Verified 3-format equivalence fixture: schematic/breadboard from espx-1-1-2-hello-world,
# wokwi diagram built inline (resistor pins swapped vs the real helloworld-idf so all 3 agree).
_EQUIV_DIAGRAM = {
    "version": 1,
    "author": "test",
    "editor": "wokwi",
    "parts": [
        {"type": "board-esp32-devkit-c-v4", "id": "esp", "top": 38.4, "left": 4.84, "attrs": {}},
        {"type": "wokwi-led", "id": "led1", "top": -3.33, "left": 153.33, "attrs": {"color": "red"}},
        {
            "type": "wokwi-resistor",
            "id": "r1",
            "top": 100.8,
            "left": 153.05,
            "rotate": 90,
            "attrs": {"value": "220"},
        },
    ],
    "connections": [
        ["led1:A", "r1:2", "green", []],
        ["r1:1", "esp:2", "green", []],
        ["led1:C", "esp:GND.3", "green", []],
    ],
    "dependencies": {},
}


def _mismatched_diagram() -> dict:
    """Inject a net mismatch: r1:1 -> esp:4 (GPIO4) instead of esp:2 (GPIO2)."""
    diagram = copy.deepcopy(_EQUIV_DIAGRAM)
    diagram["connections"] = [
        ["led1:A", "r1:2", "green", []],
        ["r1:1", "esp:4", "green", []],
        ["led1:C", "esp:GND.3", "green", []],
    ]
    return diagram


def _resistor_component(instance_id: str) -> Component:
    return Component(
        instance_id,
        "resistor",
        (Pin("1", "1", "passive", 0), Pin("2", "2", "passive", 1)),
    )


def _led_component(pins: tuple[str, ...]) -> Component:
    return Component("D1", "led", tuple(Pin(n, n, "passive", i) for i, n in enumerate(pins)))


def _widget_component() -> Component:
    """A component whose kind is not a key of maps.KIND_TO_PART_TYPE."""
    return Component("X1", "widget", ())


# ---------------------------------------------------------------------------
# check_three_format: positive (no findings) and each finding kind
# ---------------------------------------------------------------------------


def test_verified_equivalence_fixture_yields_no_findings() -> None:
    schematic = import_circuit(_ESPX / "circuit.yaml")
    breadboard = import_layout(_ESPX / "layout.yaml")
    wokwi = import_wokwi(_EQUIV_DIAGRAM)

    findings = check_three_format(schematic, breadboard, wokwi)
    assert findings == []


def test_injected_gpio_mismatch_yields_net_mismatch_errors() -> None:
    schematic = import_circuit(_ESPX / "circuit.yaml")
    breadboard = import_layout(_ESPX / "layout.yaml")
    wokwi = import_wokwi(_mismatched_diagram())

    findings = check_three_format(schematic, breadboard, wokwi)
    mismatches = [f for f in findings if f.kind == "net_mismatch"]
    assert len(mismatches) == 2
    assert all(f.severity == "error" for f in mismatches)

    absent_from_wokwi = repr(tuple(sorted({("R1", "1"), ("U1", "GPIO2")})))
    only_in_wokwi = repr(tuple(sorted({("R1", "1"), ("U1", "GPIO4")})))
    by_entity = {f.entity: f for f in mismatches}
    assert set(by_entity) == {absent_from_wokwi, only_in_wokwi}
    assert by_entity[absent_from_wokwi].present_in == ("schematic", "breadboard")
    assert by_entity[absent_from_wokwi].absent_in == ("wokwi",)
    assert by_entity[only_in_wokwi].present_in == ("wokwi",)
    assert by_entity[only_in_wokwi].absent_in == ("schematic", "breadboard")


def test_component_present_in_only_one_format_yields_missing_component_error() -> None:
    shared_net = Net("N1", (PinRef("C1", "2"), PinRef("C2", "1")), "test")
    schematic = Circuit(
        "t",
        (_resistor_component("C1"), _resistor_component("C2"), _resistor_component("C3")),
        (shared_net,),
    )
    breadboard = Circuit("t", (_resistor_component("C1"), _resistor_component("C2")), (shared_net,))
    wokwi = Circuit("t", (_resistor_component("C1"), _resistor_component("C2")), (shared_net,))

    findings = check_three_format(schematic, breadboard, wokwi)
    missing = [f for f in findings if f.kind == "missing_component"]
    assert len(missing) == 1
    assert missing[0].entity == "C3"
    assert missing[0].severity == "error"
    assert missing[0].present_in == ("schematic",)
    assert missing[0].absent_in == ("breadboard", "wokwi")


def test_findings_sorted_by_kind_then_entity() -> None:
    shared_net = Net("N1", (PinRef("C1", "2"), PinRef("C2", "1")), "test")
    schematic = Circuit(
        "t",
        (
            _resistor_component("C1"),
            _resistor_component("C2"),
            _resistor_component("C4"),
            _resistor_component("C3"),
        ),
        (shared_net,),
    )
    breadboard = Circuit("t", (_resistor_component("C1"), _resistor_component("C2")), (shared_net,))
    wokwi = Circuit("t", (_resistor_component("C1"), _resistor_component("C2")), (shared_net,))

    findings = check_three_format(schematic, breadboard, wokwi)
    missing = [f for f in findings if f.kind == "missing_component"]
    assert [f.entity for f in missing] == ["C3", "C4"]


def test_wokwi_led_pin_outside_legal_set_yields_pin_name_error() -> None:
    schematic = Circuit("t", (_led_component(("anode", "cathode")),), ())
    breadboard = Circuit("t", (_led_component(("anode", "cathode")),), ())
    wokwi = Circuit("t", (_led_component(("sideways",)),), ())

    findings = check_three_format(schematic, breadboard, wokwi)
    assert len(findings) == 1
    assert findings[0].kind == "pin_name"
    assert findings[0].severity == "error"
    assert findings[0].entity == "D1:sideways"


def test_wokwi_component_with_unmapped_kind_yields_part_type_error() -> None:
    schematic = Circuit("t", (_widget_component(),), ())
    breadboard = Circuit("t", (_widget_component(),), ())
    wokwi = Circuit("t", (_widget_component(),), ())

    findings = check_three_format(schematic, breadboard, wokwi)
    # ASSUMPTION: the spec does not state the entity for a part_type finding
    # explicitly (only pin_name gets an explicit f"{instance_id}:{pin}" format);
    # entity == instance_id is the natural reading, matching missing_component.
    assert len(findings) == 1
    assert findings[0].kind == "part_type"
    assert findings[0].severity == "error"
    assert findings[0].entity == "X1"


def test_strict_does_not_change_non_geometry_finding_severity() -> None:
    shared_net = Net("N1", (PinRef("C1", "2"), PinRef("C2", "1")), "test")
    schematic = Circuit(
        "t",
        (_resistor_component("C1"), _resistor_component("C2"), _resistor_component("C3")),
        (shared_net,),
    )
    breadboard = Circuit("t", (_resistor_component("C1"), _resistor_component("C2")), (shared_net,))
    wokwi = Circuit("t", (_resistor_component("C1"), _resistor_component("C2")), (shared_net,))

    findings = check_three_format(schematic, breadboard, wokwi, strict=True)
    missing = [f for f in findings if f.kind == "missing_component"]
    assert missing[0].severity == "error"


# ---------------------------------------------------------------------------
# Geometry drift: C1 anchor aligned, C2 drifted > 1.0mm
# ---------------------------------------------------------------------------


def _geometry_fixture() -> tuple[Circuit, Circuit, Circuit]:
    components = (_resistor_component("C1"), _resistor_component("C2"))
    net = Net("N1", (PinRef("C1", "2"), PinRef("C2", "1")), "test")
    schematic = Circuit("t", components, (net,))

    breadboard = Circuit(
        "t",
        components,
        (net,),
        placements=(
            Placement("C1", {"pins": [{"name": "1", "hole": "A1"}]}, 0.0, "breadboard", "test"),
            Placement("C2", {"pins": [{"name": "1", "hole": "A5"}]}, 0.0, "breadboard", "test"),
        ),
    )

    aligned_px = to_px("A1")
    drifted_px = to_px("A5")
    drift_offset_px = 1.5 * px_per_mm()
    wokwi = Circuit(
        "t",
        components,
        (net,),
        placements=(
            Placement("C1", {"px": aligned_px}, 0.0, "wokwi", "test"),
            Placement("C2", {"px": (drifted_px[0] + drift_offset_px, drifted_px[1])}, 0.0, "wokwi", "test"),
            Placement("__wokwi_breadboard__", {"px": (0.0, 0.0)}, 0.0, "wokwi", "wokwi/breadboard-origin"),
        ),
    )
    return schematic, breadboard, wokwi


def test_drifted_shared_component_yields_geometry_drift_warning() -> None:
    schematic, breadboard, wokwi = _geometry_fixture()
    findings = check_three_format(schematic, breadboard, wokwi)
    drift = [f for f in findings if f.kind == "geometry_drift"]
    assert len(drift) == 1
    assert drift[0].severity == "warning"
    assert drift[0].entity == "C2"
    assert re.fullmatch(r"\d+\.\d+mm > 1\.0mm", drift[0].detail)


def test_drifted_shared_component_under_strict_is_error() -> None:
    schematic, breadboard, wokwi = _geometry_fixture()
    findings = check_three_format(schematic, breadboard, wokwi, strict=True)
    drift = [f for f in findings if f.kind == "geometry_drift"]
    assert len(drift) == 1
    assert drift[0].severity == "error"


def test_devkit_anchored_wokwi_circuit_yields_no_geometry_findings() -> None:
    """No __wokwi_breadboard__ marker placement -> compare_geometry short-circuits to []."""
    schematic = import_circuit(_ESPX / "circuit.yaml")
    breadboard = import_layout(_ESPX / "layout.yaml")
    wokwi = import_wokwi(_EQUIV_DIAGRAM)  # anchored on the devkit, not a breadboard

    findings = check_three_format(schematic, breadboard, wokwi)
    assert not any(f.kind == "geometry_drift" for f in findings)


# ---------------------------------------------------------------------------
# Finding3 shape
# ---------------------------------------------------------------------------


def test_finding3_exposes_required_fields() -> None:
    finding = Finding3(
        severity="error",
        kind="missing_component",
        entity="C1",
        present_in=("schematic",),
        absent_in=("breadboard", "wokwi"),
        detail="d",
        provenance="p",
    )
    assert finding.severity == "error"
    assert finding.kind == "missing_component"
    assert finding.entity == "C1"
    assert finding.present_in == ("schematic",)
    assert finding.absent_in == ("breadboard", "wokwi")
    assert finding.detail == "d"
    assert finding.provenance == "p"


# ---------------------------------------------------------------------------
# format_three_report
# ---------------------------------------------------------------------------


def _sample_findings() -> list[Finding3]:
    return [
        Finding3("error", "missing_component", "C3", ("schematic",), ("breadboard", "wokwi"), "", ""),
        Finding3("warning", "geometry_drift", "C2", (), (), "1.5mm > 1.0mm", ""),
    ]


def test_format_three_report_summarizes_counts_and_lines() -> None:
    records, summary = format_three_report(_sample_findings())

    lines = summary.splitlines()
    assert lines[0] == "1 errors, 1 warnings"
    assert set(lines[1:]) == {
        "[error]: missing_component: C3",
        "[warning]: geometry_drift: C2",
    }
    assert len(records) == 2
    error_record = next(r for r in records if r["kind"] == "missing_component")
    assert error_record["severity"] == "error"
    assert error_record["entity"] == "C3"
    warning_record = next(r for r in records if r["kind"] == "geometry_drift")
    assert warning_record["severity"] == "warning"


def test_format_three_report_strict_promotes_warnings_to_errors() -> None:
    records, summary = format_three_report(_sample_findings(), strict=True)

    assert summary.splitlines()[0] == "2 errors, 0 warnings"
    assert all(record["severity"] == "error" for record in records)
