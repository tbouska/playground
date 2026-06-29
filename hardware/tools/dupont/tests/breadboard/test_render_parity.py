"""Render-parity (golden-SVG) tests for render_layout.py.

These tests lock the drawn SVG output of the renderer. A test fails when the
normalized rendered SVG differs from the committed golden file for that layout.

Non-determinism in matplotlib SVGs:
- ``<dc:date>`` timestamp: stripped by _normalize.
- ``clip-path="url(#pXXXXXXXX)"`` and the matching ``<clipPath id="pXXXXXXXX">``
  definition: the hex suffix is a per-render hash; replaced with a stable
  placeholder by _normalize.

Re-blessing goldens:
    Set the environment variable REBLESS_GOLDENS=1 before running to overwrite
    the golden files with the current renderer output:

        REBLESS_GOLDENS=1 uv run --with pytest --with 'matplotlib==3.11.0' --with 'pyyaml==6.0.3' \
            pytest hardware/tools/breadboard/tests/test_render_parity.py -q
"""

import os
import re
from pathlib import Path

import pytest

import render_layout

_TESTS_DIR = Path(__file__).parent
_GOLDEN_DIR = _TESTS_DIR / "fixtures" / "golden"
_FIXTURE_DIR = _TESTS_DIR / "fixtures"
_REPO_ROOT = Path(__file__).resolve().parents[5]

_CLIP_ID_RE = re.compile(r'(id="|url\(#)(p[0-9a-f]{9,})')


def _normalize(svg_text: str) -> str:
    """Strip volatile parts of a matplotlib SVG so two renders of identical
    input produce byte-identical output.

    Volatile parts observed empirically (two renders of the same layout):
    - ``<dc:date>...</dc:date>`` -- per-render timestamp.
    - ``id="pXXXXXXXX"`` and ``url(#pXXXXXXXX)`` -- per-render hex clip-path id.
    """
    # Remove the dc:date element (entire line).
    text = re.sub(r"[ \t]*<dc:date>.*?</dc:date>\n?", "", svg_text)
    # Stabilise the random clip-path id (exactly one per figure).
    text = _CLIP_ID_RE.sub(lambda m: m.group(1) + "CLIP_ID_PLACEHOLDER", text)
    return text


@pytest.fixture
def all_components_layout_path() -> Path:
    return _FIXTURE_DIR / "all_components.yaml"


@pytest.fixture
def rgb_layout_path() -> Path:
    path = _REPO_ROOT / "hardware" / "arduino-ide-sketchbook" / "keyestudio-esp32-learning-kit-basic-edition" / "rgb-led-rainbow-cycle" / "layout.yaml"
    assert path.exists(), f"RGB layout not found at {path}"
    return path


def _run_parity(layout_path: Path, golden_name: str, tmp_path: Path) -> None:
    """Render layout_path, normalize, compare to (or write) the named golden."""
    layout = render_layout.load_layout(layout_path)
    out_stem = tmp_path / golden_name
    render_layout.render(layout, out_stem)
    svg_path = out_stem.with_suffix(".svg")
    assert svg_path.exists(), f"render() did not write {svg_path}"
    rendered = _normalize(svg_path.read_text(encoding="utf-8"))

    golden_path = _GOLDEN_DIR / f"{golden_name}.svg"

    if os.environ.get("REBLESS_GOLDENS"):
        _GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(rendered, encoding="utf-8")
        return

    assert golden_path.exists(), (
        f"Golden file missing: {golden_path}. "
        f"Generate it with: REBLESS_GOLDENS=1 pytest {__file__} -q"
    )
    golden = golden_path.read_text(encoding="utf-8")
    assert rendered == golden, (
        f"Rendered SVG differs from golden for '{golden_name}'. "
        f"If this change is intentional, re-bless with: "
        f"REBLESS_GOLDENS=1 pytest {__file__} -q"
    )


def test_all_components_parity(
    all_components_layout_path: Path, tmp_path: Path
) -> None:
    _run_parity(all_components_layout_path, "all_components", tmp_path)


def test_rgb_led_rainbow_cycle_parity(
    rgb_layout_path: Path, tmp_path: Path
) -> None:
    _run_parity(rgb_layout_path, "rgb_led_rainbow_cycle", tmp_path)
