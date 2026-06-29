"""Tests for the dupont CLI (import / export / convert + fail-loud)."""

from pathlib import Path

import pytest

from dupont.cli import main
from dupont.formats.circuit.importer import import_circuit
from dupont.model.serialize import load_model

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


@pytest.fixture
def project(tmp_path: Path) -> Path:
    proj = tmp_path / "hello"
    proj.mkdir()
    (proj / "circuit.yaml").write_text(_HELLO, encoding="utf-8")
    return proj


def test_convert_round_trips_circuit(project: Path) -> None:
    assert main(["convert", "--project", str(project)]) == 0
    out = project / "hello.convert.yaml"
    assert out.exists()
    # The round-tripped circuit re-imports to the same model as the source.
    assert import_circuit(out) == import_circuit(project / "circuit.yaml")


def test_import_writes_faithful_model(project: Path) -> None:
    assert main(["import", "--project", str(project)]) == 0
    model = project / "hello.model.yaml"
    assert model.exists()
    assert load_model(model) == import_circuit(project / "circuit.yaml")


def test_export_after_import_regenerates_circuit(project: Path) -> None:
    assert main(["import", "--project", str(project)]) == 0
    assert main(["export", "--project", str(project)]) == 0
    regenerated = project / "hello.circuit.yaml"
    assert regenerated.exists()
    assert import_circuit(regenerated) == import_circuit(project / "circuit.yaml")


def test_unsupported_direction_fails_loud(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["check", "--project", str(project)])
    assert rc != 0
    err = capsys.readouterr().err
    assert "unsupported direction" in err
    assert "import, export, convert" in err


def test_unsupported_format_fails_loud(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["convert", "--project", str(project), "--format", "wokwi"])
    assert rc != 0
    err = capsys.readouterr().err
    assert "unsupported format" in err
    assert "circuit" in err
