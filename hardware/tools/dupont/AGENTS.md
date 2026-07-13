# dupont - agent guardrails

Interop program context: `dev/local/discovery/00006-format-interop-netlist-hub.md`
(architecture authority), `dev/local/prds/ROADMAP.md` (execution order).

`dupont/` is the canonical package (interchange model hub). `breadboard/` is
the legacy draw backend: it stays in the wheel, but new features must go
through the interchange model (`dupont.model`), never through
`breadboard.parse` directly.

## Invariants (hold these in every change)

1. **Fail loud, never drop.** Importers/exporters reject unmapped kinds,
   part_types, and pin names with an error naming the offender. A component
   that goes in and silently doesn't come out is a defect, not a limitation.
   (Historical violation: `import_layout`'s kind filter; fixed in PRD 00010.)
2. **One transform boundary.** Every holes/mm/px conversion goes through
   `dupont/grid/geometry.py` (`to_px`, `to_hole`, `SNAP_TOLERANCE_MM`). No
   ad-hoc unit arithmetic at export/check/placement sites - this exact class
   of bug caused the task 7/10/11 rework chain in PRD 00009.
3. **Tables are sourced, not guessed.** Mapping tables (Wokwi maps, module
   pinouts, KiCad footprints, `grid/scale.py`) carry a provenance comment
   stating where the values come from. `PX_PER_MM` is the model: measured,
   cross-checked, flagged.
4. **Nets compare canonicalized.** Cross-format identity is
   `(instance_id, pin)` membership after `canon` id minting (declaration
   order) + pin normalization. Never compare by `net_id`.
5. **Renders prove refactors.** Any change touching draw or serialization
   paths runs the golden/parity tests; per-file rollback on parity failure.
6. **Duplicated logic across languages needs a sync test.** If JS (editor)
   or any second implementation mirrors Python logic (grid constants, net
   grouping), a fixture-driven equality test binds them.

## Gaps currently tracked (do not assume these hold yet)

- Silent-drop kind filter in `formats/breadboard/importer.py` - PRD 00010.
- Single-load circuit template cap - PRD 00011.
- Dual render paths (`render_layout.py` vs model path) - PRD 00012.
- No placement engine (circuit→layout, diagram→layout blocked) - PRDs
  00013/00014.
