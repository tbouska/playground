"""Tests for dupont.render.breadboard.render_breadboard (Circuit -> SVG/PNG).

Because the interchange Circuit is a faithful transport of a placed
breadboard layout, rendering a Circuit imported from a layout.yaml must
produce a byte-identical (post-normalization) SVG to rendering that same
layout.yaml through the existing direct-parse breadboard render path. All
tests are black-box: they assert on files written and on normalized SVG
text, never on implementation internals.
"""

import re
from pathlib import Path

import pytest

from breadboard.parse import load_layout
from breadboard.render import render as render_direct
from dupont.formats.breadboard.importer import import_layout
from dupont.render.breadboard import render_breadboard

# ---------------------------------------------------------------------------
# Fixture paths (relative to the hardware/ root, three levels above this file)
# ---------------------------------------------------------------------------

_HW = Path(__file__).resolve().parents[3]
_HELLO_WORLD = _HW / "arduino-ide-sketchbook/espx/espx-1-1-2-hello-world/layout.yaml"
_RGB_RAINBOW = (
    _HW
    / "arduino-ide-sketchbook/keyestudio-esp32-learning-kit-basic-edition/rgb-led-rainbow-cycle/layout.yaml"
)

# ---------------------------------------------------------------------------
# Normalization (copied verbatim from tests/breadboard/test_render_parity.py)
# ---------------------------------------------------------------------------

_CLIP_ID_RE = re.compile(r'(id="|url\(#)(p[0-9a-f]{9,})')


def _normalize(svg_text: str) -> str:
    text = re.sub(r"[ \t]*<dc:date>.*?</dc:date>\n?", "", svg_text)
    text = _CLIP_ID_RE.sub(lambda m: m.group(1) + "CLIP_ID_PLACEHOLDER", text)
    return text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert_model_path_matches_direct_render(layout_path: Path, tmp_path: Path) -> None:
    """Render layout_path via both the model path and the direct-parse path;
    assert their normalized SVGs are equal."""
    model_stem = tmp_path / "model"
    direct_stem = tmp_path / "direct"

    render_breadboard(import_layout(layout_path), model_stem)
    render_direct(load_layout(layout_path), direct_stem)

    model_svg = _normalize(model_stem.with_suffix(".svg").read_text(encoding="utf-8"))
    direct_svg = _normalize(direct_stem.with_suffix(".svg").read_text(encoding="utf-8"))
    assert model_svg == direct_svg


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_render_breadboard_writes_svg_and_png(tmp_path: Path) -> None:
    out_stem = tmp_path / "hello_world"
    render_breadboard(import_layout(_HELLO_WORLD), out_stem)
    assert out_stem.with_suffix(".svg").exists()
    assert out_stem.with_suffix(".png").exists()


def test_hello_world_model_path_matches_direct_render(tmp_path: Path) -> None:
    _assert_model_path_matches_direct_render(_HELLO_WORLD, tmp_path)


def test_rgb_led_rainbow_cycle_model_path_matches_direct_render(tmp_path: Path) -> None:
    _assert_model_path_matches_direct_render(_RGB_RAINBOW, tmp_path)
