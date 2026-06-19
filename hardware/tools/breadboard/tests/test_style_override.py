"""Tests for user style override: --style CLI flag and top-level style: YAML key.

Covers:
- Layout.style field wired through render()
- load_layout() reading style: from YAML
- --style PATH flag via render_layout.main()
- Precedence: inline style: wins over --style path file
- Unknown override keys warn but don't crash render
"""

import sys
from pathlib import Path

import pytest
import yaml

import render_layout
from breadboard.model import Layout
from breadboard.style import load_style

_DEFAULT_BOARD_FILL = "#efeae0"
_OVERRIDE_FILL = "#123456"


def _minimal_layout(style: dict | None = None) -> Layout:
    return Layout(title="t", columns=10, components=(), style=style)


def test_inline_style_key_overrides_board_colour(tmp_path: Path) -> None:
    layout = _minimal_layout(style={"board": {"fill": _OVERRIDE_FILL}})
    render_layout.render(layout, tmp_path / "o")
    svg = (tmp_path / "o.svg").read_text(encoding="utf-8")

    assert _OVERRIDE_FILL in svg
    assert _DEFAULT_BOARD_FILL not in svg


def test_no_style_uses_default_board_colour(tmp_path: Path) -> None:
    layout = _minimal_layout(style=None)
    render_layout.render(layout, tmp_path / "o")
    svg = (tmp_path / "o.svg").read_text(encoding="utf-8")

    assert _DEFAULT_BOARD_FILL in svg
    assert _OVERRIDE_FILL not in svg


def test_style_path_file_overrides_board_colour(tmp_path: Path) -> None:
    path_fill = "#654321"
    override_file = tmp_path / "override.yaml"
    override_file.write_text(yaml.dump({"board": {"fill": path_fill}}), encoding="utf-8")

    layout = _minimal_layout(style=None)
    render_layout.render(layout, tmp_path / "o", load_style(path=override_file))
    svg = (tmp_path / "o.svg").read_text(encoding="utf-8")

    assert path_fill in svg


def test_load_layout_reads_style_key(tmp_path: Path) -> None:
    with_style = tmp_path / "with_style.yaml"
    with_style.write_text(
        "breadboard:\n  columns: 10\ncomponents: []\nstyle:\n  board:\n    fill: \"#123456\"\n",
        encoding="utf-8",
    )
    assert render_layout.load_layout(with_style).style == {"board": {"fill": "#123456"}}

    without_style = tmp_path / "without_style.yaml"
    without_style.write_text(
        "breadboard:\n  columns: 10\ncomponents: []\n",
        encoding="utf-8",
    )
    assert render_layout.load_layout(without_style).style is None


def test_inline_style_wins_over_path_file(tmp_path: Path) -> None:
    path_fill = "#aaaaaa"
    inline_fill = "#bbbbbb"

    override_file = tmp_path / "override.yaml"
    override_file.write_text(yaml.dump({"board": {"fill": path_fill}}), encoding="utf-8")

    layout = _minimal_layout(style={"board": {"fill": inline_fill}})
    merged = load_style(path=override_file, inline=layout.style)
    render_layout.render(layout, tmp_path / "o", merged)
    svg = (tmp_path / "o.svg").read_text(encoding="utf-8")

    assert inline_fill in svg
    assert path_fill not in svg


def test_unknown_override_key_still_renders(tmp_path: Path) -> None:
    layout = _minimal_layout(style={"bogus_section": {"x": 1}})
    render_layout.render(layout, tmp_path / "o")
    svg_path = tmp_path / "o.svg"

    assert svg_path.exists()
    svg = svg_path.read_text(encoding="utf-8")
    assert _DEFAULT_BOARD_FILL in svg


def test_cli_style_flag_applies_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path_fill = "#abcdef"
    override_file = tmp_path / "override.yaml"
    override_file.write_text(yaml.dump({"board": {"fill": path_fill}}), encoding="utf-8")

    layout_file = tmp_path / "layout.yaml"
    layout_file.write_text(
        "breadboard:\n  columns: 10\ncomponents: []\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["render_layout", str(layout_file), "--style", str(override_file)],
    )
    render_layout.main()

    svg = layout_file.with_suffix(".svg").read_text(encoding="utf-8")
    assert path_fill in svg
