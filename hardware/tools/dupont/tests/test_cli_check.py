"""Tests for the dupont CLI ``check`` direction (schematic<->breadboard consistency)."""

import re
from pathlib import Path

import pytest

from dupont.cli import main

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SKETCH = _REPO_ROOT / "hardware" / "arduino-ide-sketchbook"
_HELLO = _SKETCH / "espx" / "espx-1-1-2-hello-world"
_RAINBOW = _SKETCH / "keyestudio-esp32-learning-kit-basic-edition" / "rgb-led-rainbow-cycle"


@pytest.fixture
def equivalent_project(tmp_path: Path) -> Path:
    """A project whose circuit.yaml and layout.yaml describe the same circuit."""
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "circuit.yaml").write_text(
        (_HELLO / "circuit.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (proj / "layout.yaml").write_text(
        (_HELLO / "layout.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    return proj


@pytest.fixture
def mismatched_project(tmp_path: Path) -> Path:
    """A project pairing one project's circuit.yaml with a different project's
    layout.yaml, so the two sides describe different circuits."""
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "circuit.yaml").write_text(
        (_HELLO / "circuit.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (proj / "layout.yaml").write_text(
        (_RAINBOW / "layout.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    return proj


def test_check_equivalent_dual_format_project_returns_zero_and_prints_zero_summary(
    equivalent_project: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["check", "--project", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "0 errors, 0 warnings" in out


def test_check_mismatched_dual_format_projects_returns_one_and_reports_errors(
    mismatched_project: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["check", "--project", str(tmp_path)])
    assert rc == 1
    out = capsys.readouterr().out
    match = re.search(r"^(\d+) errors, (\d+) warnings$", out, flags=re.MULTILINE)
    assert match is not None
    assert int(match.group(1)) >= 1


def test_check_project_with_no_dual_format_dir_returns_one_and_notes_stderr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "circuit.yaml").write_text(
        (_HELLO / "circuit.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    # No layout.yaml anywhere under tmp_path, so no directory has both files.
    rc = main(["check", "--project", str(tmp_path)])
    assert rc == 1
    err = capsys.readouterr().err
    assert err.strip() != ""


def test_check_strict_flag_is_accepted_and_still_returns_zero_for_equivalent_project(
    equivalent_project: Path, tmp_path: Path
) -> None:
    rc = main(["check", "--project", str(tmp_path), "--strict"])
    assert rc == 0
