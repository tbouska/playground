"""Tests for the per-file ``layout.yaml`` -> model-schema migration.

Cover the migration gate (faithful ``.layout.model.yaml`` artifact,
collision-free naming) and the per-file rollback (a malformed source leaves no
artifact and is isolated from the rest of a batch).
"""

from pathlib import Path

import pytest

from dupont.formats.breadboard.importer import import_layout
from dupont.migrate import (
    MigrationError,
    MigrationReport,
    migrate_layout,
    migrate_layouts,
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

# A component whose kind cannot be mapped parses but is rejected by
# import_layout (fail-loud), so migration must roll its artifact back.
_BAD_LAYOUT = """\
breadboard:
  columns: 30
title: Bad
components:
  - kind: not_a_real_kind
    ref: X1
    legs: [E1, E5]
"""


def _layout(*parts: str) -> Path:
    path = _SKETCH.joinpath(*parts) / "layout.yaml"
    assert path.exists(), f"layout.yaml not found at {path}"
    return path


def _write_layout(directory: Path, body: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "layout.yaml"
    path.write_text(body, encoding="utf-8")
    return path


@pytest.mark.parametrize("parts", _PROJECTS, ids=[p[-1] for p in _PROJECTS])
def test_migrate_layout_writes_faithful_model_yaml(
    parts: tuple[str, ...], tmp_path: Path
) -> None:
    source = _layout(*parts)
    output = migrate_layout(source, tmp_path)

    assert output.exists()
    assert output.name == f"{parts[-1]}.layout.model.yaml"
    # The written artifact reloads to exactly the imported model.
    assert load_model(output) == import_layout(source)


def test_migrate_layout_names_output_by_project_dir(tmp_path: Path) -> None:
    # Two sources both named layout.yaml must not collide in one out_dir.
    out_a = migrate_layout(_layout("espx", "espx-1-1-2-hello-world"), tmp_path)
    out_b = migrate_layout(_layout(_KEY, "rgb-modes"), tmp_path)
    assert out_a != out_b
    assert out_a.exists() and out_b.exists()


def test_migrate_layout_rolls_back_on_malformed_source(tmp_path: Path) -> None:
    # A layout.yaml with an unmappable component kind fails import; migration
    # must leave no artifact and raise MigrationError naming the source.
    bad = _write_layout(tmp_path / "bad-project", _BAD_LAYOUT)
    out_dir = tmp_path / "out"
    with pytest.raises(MigrationError) as excinfo:
        migrate_layout(bad, out_dir)

    assert excinfo.value.source == bad
    assert list(out_dir.glob("*.layout.model.yaml")) == []  # rolled back


def test_migrate_layouts_isolates_failures(tmp_path: Path) -> None:
    good = _layout("espx", "espx-1-1-2-hello-world")
    bad = _write_layout(tmp_path / "bad-project", _BAD_LAYOUT)
    out_dir = tmp_path / "out"

    report = migrate_layouts([good, bad], out_dir)

    assert isinstance(report, MigrationReport)
    assert len(report.migrated) == 1
    assert report.migrated[0].name == "espx-1-1-2-hello-world.layout.model.yaml"
    assert report.migrated[0].exists()
    assert len(report.failed) == 1
    assert report.failed[0][0] == bad
    assert list(out_dir.glob("bad-project.layout.model.yaml")) == []  # rolled back
