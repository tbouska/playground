"""Tests for breadboard.parse.load_layout.

Verifies load_layout parses the all-components fixture into Layout/Component
value objects with the expected title, columns, component kinds, and module
pin mapping.
"""

from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_load_layout_parses_all_components_fixture() -> None:
    from breadboard.parse import load_layout
    from breadboard.model import Layout

    layout = load_layout(FIXTURES / "all_components.yaml")

    assert isinstance(layout, Layout)
    assert layout.title == "All components fixture"
    assert layout.columns == 25
    assert len(layout.components) == 16


def test_loaded_layout_preserves_component_kinds() -> None:
    from breadboard.parse import load_layout

    layout = load_layout(FIXTURES / "all_components.yaml")

    kinds = [c.kind for c in layout.components]
    assert "resistor" in kinds
    assert "led" in kinds
    assert "led-rgb" in kinds
    assert "capacitor" in kinds
    assert "diode" in kinds
    assert "transistor" in kinds
    assert "button" in kinds
    assert "module" in kinds
    assert "power" in kinds
    assert "wire" in kinds
    assert "crystal" in kinds
    assert "inductor" in kinds
    assert "buzzer" in kinds
    assert "potentiometer" in kinds
    assert "7segment" in kinds
    assert "relay" in kinds


def test_loaded_layout_module_component_has_correct_pins() -> None:
    from breadboard.parse import load_layout

    layout = load_layout(FIXTURES / "all_components.yaml")

    module = next(c for c in layout.components if c.kind == "module")
    assert module.ref == "U1"
    assert len(module.pins) == 4
    pin_map = {p.name: p.hole for p in module.pins}
    assert pin_map == {"VCC": "A10", "GND": "A14", "D2": "J10", "D3": "J14"}


def test_dict_form_legs_rejected_for_non_led_kind() -> None:
    """Dict-form `legs:` only feeds the RGB-LED `named_legs`; on any other kind it is
    silently dropped and the part renders degenerate near column 0. Reject it at parse
    time with an error that names the offending kind, rather than rendering nonsense."""
    import pytest

    from breadboard.parse import _component_from_dict

    with pytest.raises(ValueError, match="relay"):
        _component_from_dict(
            {"kind": "relay", "ref": "K1", "legs": {"COIL": "A1", "NO": "A3"}}
        )


def test_dict_form_legs_allowed_for_led_rgb() -> None:
    """The RGB LED drawer consumes dict-form legs as `named_legs`; parse must keep
    accepting it (guards the rejection above from over-reaching)."""
    from breadboard.parse import _component_from_dict

    comp = _component_from_dict(
        {"kind": "led-rgb", "ref": "D2", "legs": {"R": "C2", "K": "C3", "G": "C4"}}
    )
    assert comp.named_legs == {"R": "C2", "K": "C3", "G": "C4"}
    assert comp.legs == ()
