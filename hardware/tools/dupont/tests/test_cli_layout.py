"""Tests for the dupont CLI ``--format layout`` branch (import / export)."""

import re
from pathlib import Path

import pytest

from breadboard.parse import load_layout
from breadboard.render import render as render_direct
from dupont.cli import main
from dupont.formats.breadboard.importer import import_layout
from dupont.model.serialize import load_model

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SKETCH = _REPO_ROOT / "hardware" / "arduino-ide-sketchbook"
_SOURCE_LAYOUT = _SKETCH / "espx" / "espx-1-1-2-hello-world" / "layout.yaml"
_SOURCE_CIRCUIT = _SKETCH / "espx" / "espx-1-1-2-hello-world" / "circuit.yaml"

_CLIP_ID_RE = re.compile(r'(id="|url\(#)(p[0-9a-f]{9,})')


def _normalize(svg_text: str) -> str:
    text = re.sub(r"[ \t]*<dc:date>.*?</dc:date>\n?", "", svg_text)
    return _CLIP_ID_RE.sub(lambda m: m.group(1) + "CLIP_ID_PLACEHOLDER", text)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "layout.yaml").write_text(
        _SOURCE_LAYOUT.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return proj


def test_import_layout_writes_model_beside_source(
    project: Path, tmp_path: Path
) -> None:
    rc = main(["import", "--project", str(tmp_path), "--format", "layout"])
    assert rc == 0
    assert (project / "proj.layout.model.yaml").exists()
    written = project / "proj.layout.model.yaml"
    assert load_model(written) == import_layout(_SOURCE_LAYOUT)


def test_export_layout_renders_images_beside_model(
    project: Path, tmp_path: Path
) -> None:
    assert main(["import", "--project", str(tmp_path), "--format", "layout"]) == 0
    assert main(["export", "--project", str(tmp_path), "--format", "layout"]) == 0
    assert (project / "proj.layout.svg").exists()
    assert (project / "proj.layout.png").exists()
    render_direct(load_layout(_SOURCE_LAYOUT), tmp_path / "direct")
    exported = _normalize((project / "proj.layout.svg").read_text(encoding="utf-8"))
    direct = _normalize(
        (tmp_path / "direct").with_suffix(".svg").read_text(encoding="utf-8")
    )
    assert exported == direct
    assert (project / "proj.layout.png").stat().st_size > 0


def test_unsupported_direction_with_layout_format_fails_loud(
    project: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["check", "--project", str(tmp_path), "--format", "layout"])
    assert rc != 0
    err = capsys.readouterr().err
    assert "unsupported direction" in err


def test_circuit_export_ignores_migrated_layout_models(tmp_path: Path) -> None:
    # A dir holding BOTH a migrated circuit model and a migrated layout model:
    # the default circuit export must skip the .layout.model.yaml (its MCU pins
    # are not gpio-typed, so export_circuit would fail) and still exit 0.
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "circuit.yaml").write_text(
        _SOURCE_CIRCUIT.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (proj / "layout.yaml").write_text(
        _SOURCE_LAYOUT.read_text(encoding="utf-8"), encoding="utf-8"
    )
    assert main(["import", "--project", str(tmp_path)]) == 0
    assert main(["import", "--project", str(tmp_path), "--format", "layout"]) == 0
    assert main(["export", "--project", str(tmp_path)]) == 0
    assert (proj / "proj.circuit.yaml").exists()
