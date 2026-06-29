"""Tests for the per-file ``circuit.yaml`` -> model-schema migration.

Cover the migration gate (faithful ``.model.yaml`` artifact, collision-free
naming) and the per-file rollback (a malformed source leaves no artifact and is
isolated from the rest of a batch).
"""

from pathlib import Path

import pytest

from dupont.formats.circuit.importer import import_circuit
from dupont.migrate import (
    MigrationError,
    MigrationReport,
    migrate_circuit,
    migrate_circuits,
)
from dupont.model.serialize import load_model

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SKETCH = _REPO_ROOT / "hardware" / "arduino-ide-sketchbook"
_KEY = "keyestudio-esp32-learning-kit-basic-edition"

_PROJECTS = [
    ("espx", "espx-1-1-2-hello-world"),
    (_KEY, "rgb-led-rainbow-cycle"),
    (_KEY, "rgb-modes"),
]


def _circuit(*parts: str) -> Path:
    path = _SKETCH.joinpath(*parts) / "circuit.yaml"
    assert path.exists(), f"circuit.yaml not found at {path}"
    return path


def _write_circuit(directory: Path, body: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "circuit.yaml"
    path.write_text(body, encoding="utf-8")
    return path


@pytest.mark.parametrize("parts", _PROJECTS, ids=[p[-1] for p in _PROJECTS])
def test_migrate_circuit_writes_faithful_model_yaml(
    parts: tuple[str, ...], tmp_path: Path
) -> None:
    source = _circuit(*parts)
    output = migrate_circuit(source, tmp_path)

    assert output.exists()
    assert output.name == f"{parts[-1]}.model.yaml"
    # The written artifact reloads to exactly the source model.
    assert load_model(output) == import_circuit(source)


def test_migrate_circuit_names_output_by_project_dir(tmp_path: Path) -> None:
    # Two sources both named circuit.yaml must not collide in one out_dir.
    out_a = migrate_circuit(_circuit("espx", "espx-1-1-2-hello-world"), tmp_path)
    out_b = migrate_circuit(_circuit(_KEY, "rgb-modes"), tmp_path)
    assert out_a != out_b
    assert out_a.exists() and out_b.exists()


def test_migrate_circuit_rolls_back_on_malformed_source(tmp_path: Path) -> None:
    # A circuit.yaml missing the required 'load' key fails import; migration
    # must leave no artifact and raise MigrationError naming the source.
    bad = _write_circuit(
        tmp_path / "bad-project",
        "title: Bad\nmcu:\n  label: M\n  power: []\nchannels: []\n",
    )
    out_dir = tmp_path / "out"
    with pytest.raises(MigrationError) as excinfo:
        migrate_circuit(bad, out_dir)

    assert excinfo.value.source == bad
    assert list(out_dir.glob("*.model.yaml")) == []  # rolled back


def test_migrate_circuits_isolates_failures(tmp_path: Path) -> None:
    good = _circuit("espx", "espx-1-1-2-hello-world")
    bad = _write_circuit(
        tmp_path / "bad-project",
        "title: Bad\nmcu:\n  label: M\n  power: []\nchannels: []\n",
    )
    out_dir = tmp_path / "out"

    report = migrate_circuits([good, bad], out_dir)

    assert isinstance(report, MigrationReport)
    assert len(report.migrated) == 1
    assert report.migrated[0].name == "espx-1-1-2-hello-world.model.yaml"
    assert report.migrated[0].exists()
    assert len(report.failed) == 1
    assert report.failed[0][0] == bad
    assert list(out_dir.glob("bad-project.model.yaml")) == []  # bad one rolled back
