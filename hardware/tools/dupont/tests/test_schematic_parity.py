"""Render-parity (golden-SVG) tests for the schematic draw path.

These lock the SVG output of the schematic renderer after its migration onto the
interchange model::

    circuit.yaml --import_circuit--> Circuit --render_schematic--> SVG

A test fails when the normalized rendered SVG differs from the committed golden
for that circuit. This is the schematic migration gate (design 00007 sec.
"render parity"); the breadboard renderer keeps its own gate in
``tests/breadboard/test_render_parity.py``.

``_normalize`` mirrors the breadboard parity harness: it strips the per-render
``<dc:date>`` timestamp and the per-render ``clip-path`` hex id so two renders of
identical input are byte-equal.

Re-blessing goldens:
    REBLESS_GOLDENS=1 uv run --directory hardware/tools/dupont \
        pytest tests/test_schematic_parity.py -q
"""

import os
import re
from pathlib import Path

from dupont.formats.circuit.importer import import_circuit
from dupont.render.schematic import render_schematic

_TESTS_DIR = Path(__file__).parent
_GOLDEN_DIR = _TESTS_DIR / "fixtures" / "golden"
_REPO_ROOT = Path(__file__).resolve().parents[4]

# Mirrors breadboard tests/breadboard/test_render_parity.py::_normalize.
_CLIP_ID_RE = re.compile(r'(id="|url\(#)(p[0-9a-f]{9,})')


def _normalize(svg_text: str) -> str:
    """Strip the volatile parts of a matplotlib SVG (timestamp, clip-path id)."""
    text = re.sub(r"[ \t]*<dc:date>.*?</dc:date>\n?", "", svg_text)
    return _CLIP_ID_RE.sub(lambda m: m.group(1) + "CLIP_ID_PLACEHOLDER", text)


def _circuit_path(*parts: str) -> Path:
    path = _REPO_ROOT / "hardware" / "arduino-ide-sketchbook"
    for part in parts:
        path = path / part
    path = path / "circuit.yaml"
    assert path.exists(), f"circuit.yaml not found at {path}"
    return path


def _run_parity(circuit_path: Path, golden_name: str, tmp_path: Path) -> None:
    """Render circuit_path through the model, normalize, compare to golden."""
    circuit = import_circuit(circuit_path)
    out_stem = tmp_path / golden_name
    render_schematic(circuit, out_stem)
    svg_path = out_stem.with_suffix(".svg")
    assert svg_path.exists(), f"render_schematic did not write {svg_path}"
    rendered = _normalize(svg_path.read_text(encoding="utf-8"))

    golden_path = _GOLDEN_DIR / f"{golden_name}.svg"
    if os.environ.get("REBLESS_GOLDENS"):
        _GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(rendered, encoding="utf-8")
        return

    assert golden_path.exists(), (
        f"Golden file missing: {golden_path}. "
        f"Generate it with REBLESS_GOLDENS=1."
    )
    golden = golden_path.read_text(encoding="utf-8")
    assert rendered == golden, (
        f"Rendered SVG differs from golden for '{golden_name}'. "
        f"Re-bless with REBLESS_GOLDENS=1 if this change is intentional."
    )


def test_hello_world_schematic_parity(tmp_path: Path) -> None:
    _run_parity(
        _circuit_path("espx", "espx-1-1-2-hello-world"),
        "schematic_hello_world",
        tmp_path,
    )
