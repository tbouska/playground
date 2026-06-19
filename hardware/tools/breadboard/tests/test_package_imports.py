"""Import-smoke tests for the breadboard package public surface.

Verifies that all public symbols are importable from their new module homes
and that the top-level package re-exports share object identity with the
submodule originals.
"""

import breadboard
import breadboard.geometry
import breadboard.model
import breadboard.style


def test_geometry_symbols_importable() -> None:
    from breadboard.geometry import Geometry, LINE_ORDER

    assert Geometry is not None
    assert LINE_ORDER is not None


def test_model_symbols_importable() -> None:
    from breadboard.model import Layout, Component, Pin

    assert Layout is not None
    assert Component is not None
    assert Pin is not None


def test_style_constants_importable() -> None:
    from breadboard.style import RENDER_DPI, HOLE_RADIUS, BOARD_COLOR

    assert RENDER_DPI is not None
    assert HOLE_RADIUS is not None
    assert BOARD_COLOR is not None


def test_package_exposes_version_string() -> None:
    assert isinstance(breadboard.__version__, str)


def test_package_reexports_share_identity() -> None:
    assert breadboard.Layout is breadboard.model.Layout
    assert breadboard.Component is breadboard.model.Component
    assert breadboard.Pin is breadboard.model.Pin
    assert breadboard.Geometry is breadboard.geometry.Geometry


def test_board_symbol_importable() -> None:
    from breadboard.board import _draw_board

    assert _draw_board is not None


def test_wires_symbols_importable() -> None:
    from breadboard.wires import (
        _block_rects,
        _hits_block,
        _wire_channels,
        _wire_points,
        _hop_polyline,
        _draw_wire,
        _draw_wires,
    )

    assert _block_rects is not None
    assert _hits_block is not None
    assert _wire_channels is not None
    assert _wire_points is not None
    assert _hop_polyline is not None
    assert _draw_wire is not None
    assert _draw_wires is not None


def test_component_base_helpers_importable() -> None:
    from breadboard.components.base import (
        _leg_frame,
        _draw_leads,
        _leg_dots,
        _part_label,
        _body_quad,
        _tint,
    )

    assert _leg_frame is not None
    assert _draw_leads is not None
    assert _leg_dots is not None
    assert _part_label is not None
    assert _body_quad is not None
    assert _tint is not None


def test_render_symbol_importable() -> None:
    from breadboard.render import render

    assert render is not None


def test_entry_shim_reexports_package_functions() -> None:
    """render_layout.py is a thin shim: its ``render`` and ``load_layout`` are
    the package functions themselves, not local copies that could drift."""
    import breadboard.parse
    import breadboard.render
    import render_layout

    assert render_layout.render is breadboard.render.render
    assert render_layout.load_layout is breadboard.parse.load_layout
