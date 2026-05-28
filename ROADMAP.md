# Roadmap

SPDX-License-Identifier: GPL-3.0-or-later

Planned work not yet implemented. Items move to [CHANGELOG.md](CHANGELOG.md)
once landed. Classification and ordering follow the
[AGENTS.md Release Process](AGENTS.md#release-process):

- **PATCH** — bug fixes (security, leak, correctness, robustness) and refactors
  with zero behavior change. Within PATCH, bugfixes are ordered
  security → resource leaks → correctness → robustness; cleanups are ordered
  dead-code → decomposition → polish.
- **MINOR** — new additive functionality and public-signature changes.
- **MAJOR** — removed symbols, default changes, breaking renames.

A few entries have multiple options whose classification differs; each option's
bump level is noted inline.

## Planned

## Bug fixes (PATCH)

### Resource leaks

#### Broaden `__del__` exception guards

`ElevationGrid.__del__` (`elevation.py:222`) has no try/except — crashes during
interpreter shutdown with `AttributeError` when `__init__` was never called
(confirmed in Docker integration warnings). `SharedDEMGrid.__del__`
(`shared_dem_grid.py:190`) catches only `TypeError`, missing `AttributeError` for
late-shutdown GC where module globals are `None`. Add `(TypeError, AttributeError)`
to both, matching the pattern already in `TempDirManager.__del__`.

#### ThreadPoolExecutor leak in tile_merge

`tile_merge.py:100-102` creates `ThreadPoolExecutor(max_workers=1)` per clipped tile
without `with` or explicit `shutdown()`. Orphan executors leave worker threads
parked in `concurrent.futures.thread._threads_queues` until interpreter shutdown,
so a 200-tile run accumulates ~200 idle threads. Fix: hoist a single module-level
executor reused across calls, or wrap the `.submit()` in a `with` block.

### Correctness

#### BEL silently dropped in P2P/Batch simple-clutter mode

`compute_terminal_clutter_losses` (`clutter/advanced.py:165-222`) splits on
`advanced = context is not None and context.model == "advanced"`. The simple-mode
branch (`clutter/advanced.py:174-180`) returns a `TerminalClutterLosses` with
default `total_with_bel_db=0.0` and `rx_bel_db=0.0` — **BEL is never computed in
simple mode**.

P2P (`p2p/compute.py:184`) and Batch (`batch/outputs.py:140`) consume
`cl.total_with_bel_db` directly, so simple-clutter runs in those algorithms
produce byte-identical rasters/results whether BEL is enabled or disabled.

Coverage is unaffected: it computes BEL on a separate path
(`radio_coverage/tasks.py:127-135`) that fires in both simple and advanced modes.

**Fix:** When `context.bel_enabled` is True, call `building_entry_loss` from the
simple-mode branch at `clutter/advanced.py:174-180` and populate `rx_bel_db` /
`total_with_bel_db` before returning. Add a regression test that asserts
`total_with_bel_db > total_loss_db` for a simple-mode P2P link with BEL enabled.

#### BEL gated on clutter_enabled across all algorithms

Even after fixing the simple-mode path above, BEL still requires
`clutter_enabled=True` to take effect:

- Coverage: gate at `radio_coverage/tasks.py:128`
  (`if clutter_enabled and clutter_context is not None and clutter_context.bel_enabled`)
- P2P: `clutter_context` is built only when `p.clutter_enabled` is True
  (`p2p/compute.py:174`); without it, BEL is skipped
- Batch: same gating via `params.clutter_enabled` (`batch/outputs.py:124`)

A user enabling BEL but leaving clutter off gets a byte-identical raster to a
BEL-off run, with no warning.

**Why this is wrong:** BEL models a receiver inside a building. It is
physically independent of outdoor terrain clutter — a rural receiver inside a
thermally-efficient building can have 25–35 dB BEL even when outdoor clutter
loss is zero. The current gating ties two unrelated effects.

**Fix:** Decouple BEL from `clutter_enabled`. Compute it whenever `bel_enabled`
is True, regardless of clutter state. Cleanest path: lift BEL out of the
clutter pipeline into a standalone helper that takes only the BEL inputs
(`frequency_mhz`, `bel_building_type`, `bel_elevation_angle_deg`, `percentile`)
and is applied to `prx` after the clutter total, with no precondition on
`clutter_enabled`. Update UI so BEL parameters are visible/enabled even when
"Clutter Correction" is off.

Add regression tests:
- P2P with `clutter_enabled=False, bel_enabled=True` produces non-zero BEL
- Coverage with `clutter_enabled=False, bel_enabled=True` produces a raster
  that differs from the same run with `bel_enabled=False`

#### Proxy realm host/port validation

`contour/pipeline.py:60-64` formats `proxy_base_url` from `parsed_realm.hostname`
and `.port` without a None check. A malformed realm URL (e.g. a bare hostname with
no scheme) yields `http://None:None` and downloads fail silently. Validate both
fields, surface a clear `feedback.pushWarning`, and return None instead of building
a broken opener.

#### Omni-preset silent-snap warning

When `ANTENNA_PRESET=0` (Omni), `radio_coverage/params.py:220-223` forces
`antenna_az=None` and `antenna_bw_override=360.0` regardless of the
`ANTENNA_AZ`, `ANTENNA_BW`, and `DOWNTILT_DEG` values the user supplied. The
snap is intentional (omni means omni), but it is **silent** — the user gets no
feedback that their directional inputs were discarded.

**Evidence from run08:** four scenarios (`cov_antenna_downtilt`,
`cov_antenna_sector_65deg`, `cov_antenna_downtilt_only`,
`cov_antenna_sector_65deg_only`) all passed `ANTENNA_PRESET=0` with non-default
BW (65) or DOWNTILT (6) values, and produced byte-identical rasters to the
omni baseline (md5 `d3187996…`). A reasonable test author assumed the
parameters would take effect; the plugin gave no hint they had not.

**Fix:** When `ANTENNA_PRESET=0` and any of `ANTENNA_AZ`, `ANTENNA_BW != 360.0`,
or `DOWNTILT_DEG != 0.0` is set, emit a single `feedback.pushInfo` line such as:

> "Note: ANTENNA_BW=65.0 and DOWNTILT_DEG=6.0 ignored — preset=Omni snaps both
> to omnidirectional defaults. Choose preset=Custom (or a sector preset) to
> apply directional values."

Apply the same guard to the Comparison and Batch algorithms (which share
`shared_params.add_advanced_itm_params`). Add a regression test that asserts
the info line is pushed when the snap fires.

#### Project-relative output paths for temporary layers

When coverage or P2P is run as "Temporary Output", the raster and marker GPKG
are written to `/tmp/NoWires-<user>/`. The paths are stored in the QGIS project
file but `/tmp` is cleaned by `systemd-tmpfiles` on reboot — layers are missing
after reopen. Moving the project to another computer breaks the paths entirely.

**Affected paths:**

| Algorithm | File | Temporary output written to |
|-----------|------|----------------------------|
| Coverage | `algorithm/coverage.py:87` | `coverage_prx.tif` |
| Coverage | `algorithm/coverage.py:148` | `tx_marker.gpkg` |
| P2P | `p2p/compute.py:193` | `profile_line.gpkg`, `fresnel_poly.gpkg`, `markers.gpkg` |

DEM/WorldCover caches, intermediate merges, and contour outputs are already
transient or user-specified — not affected.

**Design:**

Extract a shared helper that detects whether the QGIS project has been saved:

```python
def _project_or_temp_dir(tmp_mgr, context, feedback, name):
    proj = context.project().fileName()
    if proj:
        out = os.path.join(os.path.dirname(proj), "nowires_" + name)
        os.makedirs(out, exist_ok=True)
        return out
    out = tmp_mgr.make_dir(name, persistent=True)
    tmp_mgr.warn_persistent(feedback)
    return out
```

- Saved project → write to `<project_dir>/nowires_coverage/` (or `nowires_p2p/`)
- Unsaved project → fall back to existing `/tmp` behavior

**Portability:** Cross-machine transfer works when the user enables QGIS project
settings → General → "Save paths as relative". QGIS normalises absolute paths to
`./nowires_coverage/` on save and resolves `./` relative to the project file on
open. Same-machine reboot survival works without any user action.

**Classification note:** PATCH because the saved-project case currently produces
broken behavior (data loss on reboot). The conditional output-path logic is
additive but framed as a robustness fix.

#### K-factor parameter does not affect ITM propagation prediction

The P2P/Batch UI exposes `K_FACTOR_PRESET` with options labelled
"Sub-refractive / Geometric / Standard atmosphere / Super-refractive /
Strong super-refractive". The label strongly implies the value affects propagation
prediction; in fact it only affects Fresnel-zone/LOS curvature display.

**Call chain proves k_factor never reaches ITM:**

`itm_p2p_loss` (`radio.py:200-213`) signature accepts no `k_factor`:
```
itm_p2p_loss(h_tx, h_rx, profile, climate, N0, f__mhz, polarization,
             epsilon, sigma, mdvar, time_pct, location_pct, situation_pct)
```

All three callers omit it:
- `p2p/compute.py:141-144`
- `batch/outputs.py:105-118`
- `radio_coverage/compute.py:81-94`

`k_factor` is used only in:
- `fresnel.py:52,67,86,95` — `earth_bulge` and `fresnel_profile_analysis` (LOS curvature + Fresnel clearance geometry)
- `p2p/report_display.py:101`, `p2p/chart.py:116`, `report/payloads.py:84` — display attribution only

**Why this is not "pass k_factor to ITM":** The Longley-Rice ITM algorithm
derives its own effective Earth radius internally from surface refractivity N0;
that is how the standard works. The bundled `itm` package has no k_factor input
parameter. So the propagation prediction already responds to refractivity — it
just responds to N0, not to k.

**Fix options:**

1. **Relabel/document** *(PATCH — this section)*. Rename the parameter
   "Fresnel Earth-radius factor" and add a tooltip explaining it affects only
   Fresnel/LOS display, not ITM loss. Direct users wanting to model anomalous
   refractivity to the N0 advanced ITM parameter. Smallest blast radius.
2. **Couple preset to N0** *(MAJOR — default change)*. Map each preset to a
   representative N0 value (sub-refractive → low N0, super-refractive → high
   N0) so changing the preset changes propagation prediction too. Requires
   care: presets currently let the user pick k independent of N0, and these
   two are physically related — coupling them removes a degree of freedom that
   some users may rely on. Use an opt-in "tie k-factor to N0" checkbox if
   going this route *(this opt-in form is MINOR — additive)*.

Either change must update the user-facing docs to remove the implication that k
affects propagation directly.

### Robustness

#### Contiguous DEM array after south-up flip

`elevation.py:143` assigns `self.data = self.data[::-1]`, producing a reversed
view rather than a contiguous copy. The sibling `clutter/grid.py:83` already does
`data[::-1].copy()` — match it (`np.ascontiguousarray(self.data[::-1])`) so the
bilinear hot path operates on contiguous memory.

## Cleanups (PATCH)

### Dead code

#### Remove dead `contour_shp_path is None` check in contour algorithm

`algorithm/contour.py:205-207` checks `if contour_shp_path is None` but
`generate_contour_lines()` (`contour/generation.py:71`) never returns `None` —
it either returns the path or raises `RuntimeError`. The `None` branch is
unreachable. Either remove it or replace with a feature-count validation.

#### Remove dead try/finally in P2P algorithm

`algorithm/p2p.py:182-191` wraps `run_p2p_analysis(p2p_params)` in `try/finally`
where the finally body is `pass` plus an explanatory comment. The wrapper does
nothing — drop it and keep the comment near the call site.

### Decomposition

#### Split `algorithm/coverage.py` before next addition

`algorithm/coverage.py` is at exactly 300 lines — the AGENTS.md cap. Any new
helper or parameter forces an emergency extraction. Pre-emptively move
`_build_clutter_context` and `_write_coverage_outputs` into a new
`radio_coverage/coverage_outputs.py`. Golden-file tests
(`tests/test_report_export_golden.py`) verify zero behavior change.

#### Decompose `download_tile_with_retry` into staged helpers

`tile_download_base.py:53-219` fires every function-level biomarker at once:
CCN 53, nesting 8, 155 lines, 11 parameters, 15 commits of churn. It is the
single most extreme function in the repo and is still being modified, so each
future change pays the complexity tax. The function is really two functions
glued together (cache check + retry loop) with a tangled HTTP-error tree.

**Extractions, in order of leverage:**

1. **`_serve_from_cache(local_tif, base_name_label, feedback) -> str | None`** —
   pull out lines 64-91 (the cache-hit / checksum-verify / cleanup block).
   Drops ~30 lines of nested `if`s out of the retry loop.

2. **`_download_to_tmp(opener, tile_url, tmp_path, base_url, socket_timeout,
   max_bytes, base_name_label, feedback) -> int | None`** — lines 108-144. Just
   the HTTP request, redirect check, content-length validation, and chunked
   write. No retry logic. Returns bytes received or `None` on cancel/cap.

3. **`_classify_http_error(e, attempt, max_retries) -> tuple[Action, float]`** —
   collapse the 404 / 408,425,429 / 5xx / other tree at lines 176-204 into a
   small dispatcher returning `(GIVE_UP | RETRY_AFTER(s) | RETRY_BACKOFF)`. This
   is the highest-leverage extraction; the nested `if/elif` is the main reason
   CCN reached 53.

4. **`_validate_downloaded_tile(tmp_path) -> bool`** — `gdal.Open` + raster
   dimension/band check from lines 159-170.

After extraction, `download_tile_with_retry` becomes ~30 lines: cache check →
for attempt in range → `_download_to_tmp` → `_validate_downloaded_tile` → break.
Behavior identical; nesting drops from 8 to 3; each helper is independently
unit-testable. Use existing `tests/test_tile_download_base.py` patterns and add
focused tests for the error-classification matrix.

All extracted helpers are underscore-prefixed (private); behavior is byte-identical.
Pure refactor → PATCH per AGENTS.md.

#### Decompose `run_p2p_analysis` into pipeline stages

`p2p/compute.py:86-260` is 174 lines of straight-line code that mixes nine
distinct stages. It combines high churn (20 commits, 10× the repo's p80) with
high complexity (CCN 20, nesting 4). It does not need cleverness — just
slicing.

**Stage split:**

```
_validate_and_compute_geometry(p)               -> bounds, dist_m, pad
_acquire_clutter_grid(p, bounds)                -> (clutter_grid, owns)
_load_terrain_profile(p, bounds)                -> (distances, elevations, pfl)
_compute_propagation(p, pfl)                    -> (result, loss_db)
_compute_fresnel(distances, elevations, p)      -> fresnel data tuple
_compute_link_budget(p, loss_db, fresnel, cl)   -> (prx_dbm, margin_db, ant_adj)
_write_output_layers(p, srs, tmp_mgr, ...)      -> paths tuple
_build_and_write_reports(p, payload_inputs)     -> report_payload
_publish_to_qgis(p, paths, chart_kwargs)
```

`run_p2p_analysis` becomes ~30 lines: a sequence of these calls with the outer
`try/finally` retained for `tmp_mgr.cleanup()` and `clutter_grid.close()`. The
`feedback.setProgress(5/30/50/70/90/100)` calls remain in the orchestrator —
they are sequencing markers, not logic.

Behavior must be byte-identical; golden-file tests
(`tests/test_report_export_golden.py` and the P2P contract tests) verify this.
Do this after the dataclass migration in the Features section — the slices fall
out naturally once the multi-arg helper calls are bundled.

All extracted helpers are underscore-prefixed (private); `run_p2p_analysis`
keeps its existing public signature. Pure refactor → PATCH.

#### Decompose `compute_coverage` into pipeline stages

`radio_coverage/engine.py:101-207` is one of only two functions in the repo
flagged as a brain method (81 NLOC, CCN 10, 8 dependents). It takes 30+
parameters and orchestrates five distinct stages in a single function body,
mirroring the same shape as `run_p2p_analysis` — different domain, identical
structural problem.

**Stage split:**

```
_compute_coverage_axes(tx_lat, tx_lon, radius_km, grid_size)
    -> (bounds, lats, lons)
_build_antenna_and_clutter_context(params, elev_grid, ...)
    -> (antenna_config, clutter_context, tx_clutter_loss)
_emit_simple_clutter_warning(params, feedback)               # the percentile warning
_allocate_result_grids(grid_size)
    -> (prx, loss, itm_loss, clutter_loss, clutter_rx_db, bel_rx_db, grid_meta)
_execute_and_aggregate(tasks, grid_data, grid_meta, grids, feedback)
    -> (cancelled, failed, done)
```

`compute_coverage` becomes a ~25-line orchestrator: build axes → build context →
build tasks → allocate grids → execute → return `CoverageResult`.

**Sequencing:** This must land *after* the dataclass-parameter migration
in the Features section — the 30+ positional/keyword arguments need to bundle
into `CoverageAnalysisParams` first, otherwise each helper signature becomes
its own 15-parameter eyesore. Order:

1. Dataclass migration for `compute_coverage` (uses existing
   `CoverageAnalysisParams` from `radio_coverage/analysis_params.py`) — MINOR
2. Land the `run_p2p_analysis` split — establishes the pipeline-stage pattern
3. Port the same pattern here

`tests/test_coverage_engine.py` and `tests/test_coverage_engine_extended.py`
provide regression coverage; behavior must be byte-identical. Pure refactor
after the dataclass migration → PATCH.

#### Decompose remaining functions over 100 lines

Six functions still exceed the 100-line single-responsibility threshold after
the targeted decompositions above land:
`build_coverage_tasks()` (189), `show_profile_chart()` (172),
`add_panel_params()` (156), `_compute_single_link()` (145),
`write_fresnel_zone()` (117), `clutter_loss_saalos()` (110).

Each should split into 2-3 focused helpers per the 300-line file gate convention.
Behavior preserved by the existing golden-file tests.

### Polish

#### Add unit tests for `batch/params.py`

`batch/params.py` is a heavily depended-on module (16 dependents) with no
focused unit tests of its own. It is referenced by
`tests/test_batch_writer.py` and `tests/_qgis_mocks.py`, but those exercise
it incidentally rather than locking down its behavior.

Follow the `tests/test_dataclass_params.py` pattern that exists for
`CoverageAnalysisParams`. Cover: validation branches, default values,
parameter-registration order, QGIS-parameter to dataclass extraction.
Unit-testable with `tests/_qgis_mocks.py` — no QGIS runtime required.
Expect ~80 test LOC.

#### Add type hints to `antenna.py`, `nowires.py`, and `radio.py`

These three core modules have the highest concentration of untyped function
arguments. The rest of the codebase is well-typed. Closing this gap would enable
`mypy --strict` on the full project.

#### Document NoWires package-name requirement

`__init__.py:74` does `from NoWires.nowires import NoWiresPlugin` and every other
module uses `from NoWires.*` imports. The plugin install directory must be exactly
`NoWires` for any import to resolve — a clone into `nowires_qgis_plugin/` or any
QGIS-manager slug other than `NoWires` breaks the plugin. Either document the
requirement in README/INSTALL or convert to package-relative imports.

## Features (MINOR)

### Reopenable P2P profile chart

Closing the P2P chart dock destroys the widget and drops all profile data —
the chart can only be recovered by re-running the algorithm. Store the last
`chart_kwargs` on the `show_profile_chart` module and add a "Reopen P2P Chart"
menu action so the graph is reopenable without recomputation.

### Proxy auth wired into all algorithms

`setup_proxy_opener` is called from `algorithm/contour.py:161` only. Coverage, P2P,
Batch, and Comparison invoke `ensure_dem_for_area` and `ensure_clutter_grid_for_area`
without any proxy, so users behind authenticated proxies cannot run those four
algorithms. Add `QgsProcessingParameterAuthConfig` to each, thread `proxy_opener`
through `ensure_dem_for_area` (already supported) and through
`ensure_worldcover_for_area` → `download_worldcover_tiles` (parameter needs adding).

Adds new processing parameters → MINOR.

### Migrate high-arity functions to dataclass parameters

Four functions take 19-34 positional/keyword arguments, well past the point
where call sites become fragile to argument-order mistakes. The dataclass
infrastructure already exists (`radio_coverage/analysis_params.py`,
`p2p/analysis_params.py`); these functions just never migrated.

**`build_coverage_report_payload_for_grid` (`radio_coverage/reporting.py:53`) —
34 parameters.** Group into:

- `@dataclass CoverageGrids`: `prx_grid`, `loss_grid`, `itm_loss_grid`,
  `clutter_loss_grid`, `clutter_rx_db_grid`, `bel_rx_db_grid` + bounding box
  (`min_lat`, `max_lat`, `min_lon`, `max_lon`).
- Reuse `CoverageAnalysisParams` for radio config: `f_mhz`, `polarization`,
  `climate`, `time_pct`, `location_pct`, `situation_pct`, `tx_power`,
  `tx_gain`, `rx_gain`, `cable_loss`, `rx_sens`, `tx_h`, `rx_h`, `radius_km`,
  `grid_size`, `antenna_preset`, `clutter_enabled`, `clutter_source`.
- Keep `tx_clutter_for_report`, `extra_inputs`, `clutter_model` as explicit
  kwargs.

After: ~3 args (`CoverageGrids`, `CoverageAnalysisParams`, plus the 3 extras).

**`_write_p2p_output_layers` (`p2p/outputs_internal.py`), `show_profile_chart`
(`p2p/chart.py`), `compute_itm_p2p` (`radio_coverage/compute.py`) — 19 each.**
Most parameters already live in `P2PAnalysisParams`. Pass the params object
plus function-specific outputs (file paths, computed arrays).

Migrate one function at a time; each migration is mechanical and
behavior-preserving. Update callers, then run the existing test suite — no new
tests needed since behavior does not change.

This work makes the `run_p2p_analysis` and `compute_coverage` decompositions
significantly cheaper: the 19-arg `_write_p2p_output_layers` call at
`p2p/compute.py:198-204` becomes a one-liner.

**Classification:** the three non-underscore functions
(`build_coverage_report_payload_for_grid`, `show_profile_chart`,
`compute_itm_p2p`) are public — signature change escalates to MINOR per
AGENTS.md. `_write_p2p_output_layers` is private (PATCH on its own) but
bundles into the same release.

Pre-flight: run `grep -r "from NoWires" -- ..` outside the plugin tree per
AGENTS.md; any external importer forces this to MINOR even for the private one.

### Wire or remove `remember_nowires_3d_layers`

`three_d.py:100` defines `remember_nowires_3d_layers(project, dem_layer,
coverage_layer, contour_layer)` which writes layer IDs to project-scope entries
(`ENTRY_KEY_LAST_DEM`, `ENTRY_KEY_LAST_COVERAGE`, `CONTOUR_LAYER_KEY`). Its
sibling `resolve_nowires_3d_layers` (`three_d.py:114`) reads those keys at
`three_d.py:166`, but **nothing in the codebase ever calls the writer**. The
only reference is `tests/test_3d_support_contract.py:22`, which only asserts
the function string exists in the source.

`resolve_nowires_3d_layers` is consumed by `open_nowires_3d_view`, so the
3D-viewer flow reads stored layer IDs but they are always empty — the
"remember last layers" feature is half-implemented.

**Two paths:**

1. **Wire it up** *(MINOR — additive functionality)*. Most likely the original
   intent. Call `remember_nowires_3d_layers(project, dem_layer=...,
   coverage_layer=..., contour_layer=...)` at the points where
   coverage/contour/DEM layers are added to the QGIS project — roughly three
   call sites in `p2p/compute.py`, `algorithm/coverage.py`, and
   `algorithm/contour.py`. After this, "Open 3D View" picks up the layers
   from the last analysis run automatically.

2. **Delete it** *(PATCH if grep confirms no external callers; MAJOR otherwise
   per AGENTS.md "removed symbol")*. Remove `remember_nowires_3d_layers` and
   the contract-test assertion at `tests/test_3d_support_contract.py:22`. Also
   remove `resolve_nowires_3d_layers` if the 3D viewer should always prompt
   for layers explicitly. The function names are internal-style (`remember_*`
   / `resolve_*`) and no external consumers are documented. Run
   `grep -r "from NoWires" -- ..` outside the plugin tree to confirm before
   committing to PATCH.

Do not keep both halves with the write side unwired — half-removed pairs rot
into deeper confusion on the next refactor. Decision needed; either fix is
small (under 30 minutes).
