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


def test_import_writes_each_model_beside_its_source(tmp_path: Path) -> None:
    root = tmp_path / "root"
    sketch_a = root / "sketch_a"
    sketch_b = root / "sketch_b"
    sketch_a.mkdir(parents=True)
    sketch_b.mkdir(parents=True)
    (sketch_a / "circuit.yaml").write_text(_HELLO, encoding="utf-8")
    (sketch_b / "circuit.yaml").write_text(_HELLO, encoding="utf-8")

    assert main(["import", "--project", str(root)]) == 0

    model_a = sketch_a / "sketch_a.model.yaml"
    model_b = sketch_b / "sketch_b.model.yaml"
    assert model_a.exists()
    assert model_b.exists()

    assert not (root / "sketch_a.model.yaml").exists()
    assert not (root / "sketch_b.model.yaml").exists()

    assert load_model(model_a) == import_circuit(sketch_a / "circuit.yaml")
    assert load_model(model_b) == import_circuit(sketch_b / "circuit.yaml")


def test_unsupported_direction_fails_loud(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["wokwi", "--project", str(project)])
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
