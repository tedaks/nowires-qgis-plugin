# Roadmap

SPDX-License-Identifier: GPL-3.0-or-later

Planned work not yet implemented. Items move to [CHANGELOG.md](CHANGELOG.md) once landed.

## Planned

### Broaden `__del__` exception guards

`ElevationGrid.__del__` (`elevation.py:222`) has no try/except — crashes during
interpreter shutdown with `AttributeError` when `__init__` was never called
(confirmed in Docker integration warnings). `SharedDEMGrid.__del__`
(`shared_dem_grid.py:190`) catches only `TypeError`, missing `AttributeError` for
late-shutdown GC where module globals are `None`. Add `(TypeError, AttributeError)`
to both, matching the pattern already in `TempDirManager.__del__`.

### Decompose functions over 100 lines

Ten functions exceed the 100-line single-responsibility threshold:
`build_coverage_tasks()` (189), `run_p2p_analysis()` (174),
`show_profile_chart()` (172), `download_tile_with_retry()` (166),
`add_panel_params()` (156), `_compute_single_link()` (145),
`write_fresnel_zone()` (117), `clutter_loss_saalos()` (110),
`build_coverage_report_payload_for_grid()` (108), `compute_coverage()` (106).

Each should split into 2-3 focused helpers per the 300-line file gate convention.

### Add type hints to `antenna.py`, `nowires.py`, and `radio.py`

These three core modules have the highest concentration of untyped function
arguments. The rest of the codebase is well-typed. Closing this gap would enable
`mypy --strict` on the full project.

### Test harness improvements (runner repository)

- expects-error mechanism for intentional guard-rail exceptions
- noisy/duplicated warning dedup in `comprehensive-tests-v4.py` analyzers
- mislabeled test descriptions (conservative/optimistic swap, polarization name)

