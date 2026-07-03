"""Render-parity tests through the migrated layout model.

A layout migrated to the interchange model and reloaded must render to a
byte-identical (post-normalization) SVG as the same layout.yaml rendered
through the existing direct-parse breadboard path. This locks the full
migrate -> serialize -> load -> render chain end to end.
"""

import re
from pathlib import Path

import pytest

from breadboard.parse import load_layout
from breadboard.render import render as render_direct
from dupont.formats.breadboard.importer import import_layout
from dupont.migrate import migrate_layout
from dupont.model.serialize import load_model
from dupont.render.breadboard import render_breadboard

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SKETCH = _REPO_ROOT / "hardware" / "arduino-ide-sketchbook"
_KEY = "keyestudio-esp32-learning-kit-basic-edition"

_PROJECTS = [
    ("espx", "espx-1-1-2-hello-world"),
    (_KEY, "rgb-led-rainbow-cycle"),
    (_KEY, "rgb-modes"),
]

# ---------------------------------------------------------------------------
# Normalization (copied verbatim from tests/test_render_breadboard.py)
# ---------------------------------------------------------------------------

_CLIP_ID_RE = re.compile(r'(id="|url\(#)(p[0-9a-f]{9,})')


def _normalize(svg_text: str) -> str:
    text = re.sub(r"[ \t]*<dc:date>.*?</dc:date>\n?", "", svg_text)
    text = _CLIP_ID_RE.sub(lambda m: m.group(1) + "CLIP_ID_PLACEHOLDER", text)
    return text


def _layout(*parts: str) -> Path:
    path = _SKETCH.joinpath(*parts) / "layout.yaml"
    assert path.exists(), f"layout.yaml not found at {path}"
    return path


@pytest.mark.parametrize("parts", _PROJECTS, ids=[p[-1] for p in _PROJECTS])
def test_migrated_layout_model_render_matches_direct_render(
    parts: tuple[str, ...], tmp_path: Path
) -> None:
    source = _layout(*parts)

    written = migrate_layout(source, tmp_path)
    model = load_model(written)
    render_breadboard(model, tmp_path / "viamodel")

    render_direct(load_layout(source), tmp_path / "direct")

    viamodel_svg = _normalize(
        (tmp_path / "viamodel").with_suffix(".svg").read_text(encoding="utf-8")
    )
    direct_svg = _normalize(
        (tmp_path / "direct").with_suffix(".svg").read_text(encoding="utf-8")
    )
    assert viamodel_svg == direct_svg
