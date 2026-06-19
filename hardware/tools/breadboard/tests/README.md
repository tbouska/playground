# Breadboard renderer tests

Behavior-lock + render-parity suite for `../render_layout.py`. Run from the repo root:

```bash
uv run --with pytest --with 'matplotlib==3.11.0' --with 'pyyaml==6.0.3' \
    pytest hardware/tools/breadboard/tests
```

`matplotlib` is pinned because the golden SVGs in `fixtures/golden/` were blessed
against 3.11.0; a different version can shift drawn coordinates and fail
`test_render_parity.py` (see its module docstring). Bump the pin and re-bless together.

## What's covered

- `test_resistor.py` — `_parse_ohms` / `_format_ohms` / `_resistor_bands`.
- `test_geometry.py` — `Geometry.hole` address → coordinate mapping.
- `test_wires.py` — `_wire_channels` lane selection and `_hop_polyline` vertex counts.
- `test_render_parity.py` — renders `fixtures/all_components.yaml` and the real
  `rgb-led-rainbow-cycle/layout.yaml`, then compares the normalized SVG to a committed golden.

## Re-blessing goldens

When a renderer change intentionally alters drawn output:

```bash
REBLESS_GOLDENS=1 uv run --with pytest --with 'matplotlib==3.11.0' --with 'pyyaml==6.0.3' \
    pytest hardware/tools/breadboard/tests/test_render_parity.py
```

Review the golden diff before committing.
