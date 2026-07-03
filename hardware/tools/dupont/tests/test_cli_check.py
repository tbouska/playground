"""Tests for the dupont CLI ``check`` direction (schematic<->breadboard consistency)."""

import json
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


def test_check_isolates_a_failing_dual_format_dir_and_still_processes_others(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    good = tmp_path / "good"
    good.mkdir()
    (good / "circuit.yaml").write_text(
        (_HELLO / "circuit.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (good / "layout.yaml").write_text(
        (_HELLO / "layout.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )

    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "circuit.yaml").write_text(
        (_HELLO / "circuit.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (bad / "layout.yaml").write_text(
        "title: bad\n"
        "breadboard: {columns: 10}\n"
        "components:\n"
        "  - {kind: capacitor, ref: C1, legs: [A1, A2]}\n",
        encoding="utf-8",
    )

    rc = main(["check", "--project", str(tmp_path)])

    captured = capsys.readouterr()
    assert rc == 1
    assert captured.err.strip() != ""
    assert "fail" in captured.err.lower()
    assert bad.name in captured.err
    match = re.search(r"^(\d+) errors, (\d+) warnings$", captured.out, flags=re.MULTILINE)
    assert match is not None


# ---------------------------------------------------------------------------
# Three-format check: a dir with circuit.yaml + layout.yaml + diagram.json
# runs check_three_format instead of the two-format check_connectivity path.
# ---------------------------------------------------------------------------

# Verified 3-format equivalence fixture (same as tests/test_check_geometry.py):
# schematic/breadboard from espx-1-1-2-hello-world, wokwi diagram built inline
# (resistor pins swapped vs the real helloworld-idf so all 3 agree).
_EQUIV_WOKWI_DIAGRAM = {
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


def _mismatched_wokwi_diagram() -> dict:
    """Inject a net mismatch: r1:1 -> esp:4 (GPIO4) instead of esp:2 (GPIO2)."""
    diagram = json.loads(json.dumps(_EQUIV_WOKWI_DIAGRAM))
    diagram["connections"] = [
        ["led1:A", "r1:2", "green", []],
        ["r1:1", "esp:4", "green", []],
        ["led1:C", "esp:GND.3", "green", []],
    ]
    return diagram


@pytest.fixture
def three_format_project(tmp_path: Path) -> Path:
    """A project with circuit.yaml + layout.yaml + diagram.json describing the
    same circuit in all three formats (see espx-1-1-2-hello-world)."""
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "circuit.yaml").write_text(
        (_HELLO / "circuit.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (proj / "layout.yaml").write_text(
        (_HELLO / "layout.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (proj / "diagram.json").write_text(json.dumps(_EQUIV_WOKWI_DIAGRAM), encoding="utf-8")
    return proj


def test_check_three_format_equivalent_project_returns_zero_and_prints_zero_summary(
    three_format_project: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["check", "--project", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "0 errors, 0 warnings" in out


def test_check_three_format_injected_mismatch_returns_one_and_reports_errors(
    three_format_project: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (three_format_project / "diagram.json").write_text(
        json.dumps(_mismatched_wokwi_diagram()), encoding="utf-8"
    )
    rc = main(["check", "--project", str(tmp_path)])
    assert rc == 1
    out = capsys.readouterr().out
    match = re.search(r"^(\d+) errors, (\d+) warnings$", out, flags=re.MULTILINE)
    assert match is not None
    assert int(match.group(1)) >= 1


def test_check_project_mixing_two_and_three_format_dirs_reports_each_once(
    three_format_project: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A two-format-only dir alongside a three-format dir: both get checked, and the
    three-format dir must NOT also be reported by the two-format loop (no double report)."""
    two_format = tmp_path / "two_format"
    two_format.mkdir()
    (two_format / "circuit.yaml").write_text(
        (_HELLO / "circuit.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (two_format / "layout.yaml").write_text(
        (_HELLO / "layout.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )

    rc = main(["check", "--project", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.count("0 errors, 0 warnings") == 2
