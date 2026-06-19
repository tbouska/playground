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
    assert len(layout.components) == 10


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


def test_loaded_layout_module_component_has_correct_pins() -> None:
    from breadboard.parse import load_layout

    layout = load_layout(FIXTURES / "all_components.yaml")

    module = next(c for c in layout.components if c.kind == "module")
    assert module.ref == "U1"
    assert len(module.pins) == 4
    pin_map = {p.name: p.hole for p in module.pins}
    assert pin_map == {"VCC": "A10", "GND": "A14", "D2": "J10", "D3": "J14"}
