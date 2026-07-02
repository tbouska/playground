"""Tests for the schematic render entry point (standalone PEP-723 script)."""

import subprocess
from pathlib import Path

_HELLO = """\
title: ESP32 Hello World
mcu:
  label: ESP32-WROOM-32 DevKit
  power:
    - pin: GND
      net: GND
load:
  label: LED
  common:
    pin: K
    net: GND
channels:
  - gpio: GPIO2
    load_pin: A
    resistor: { ref: R1, value: "220" }
"""

_ENTRY = Path(__file__).parent.parent / "render_schematic.py"


def test_schematic_entry_renders_from_foreign_cwd(tmp_path: Path) -> None:
    circuit = tmp_path / "circuit.yaml"
    circuit.write_text(_HELLO, encoding="utf-8")

    result = subprocess.run(
        ["uv", "run", "--script", str(_ENTRY.resolve()), str(circuit)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=300,
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "circuit.svg").exists()


def test_schematic_entry_declares_inline_deps() -> None:
    text = _ENTRY.read_text(encoding="utf-8")

    assert "# /// script" in text
    assert "matplotlib" in text
    assert "schemdraw" in text
    assert "pyyaml" in text
