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

### Correctness

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

**Fix options (option 1 landed in v1.7.0; options 2-3 still open):**

1. **Couple preset to N0** *(MAJOR — default change)*. Map each preset to a
   representative N0 value (sub-refractive → low N0, super-refractive → high
   N0) so changing the preset changes propagation prediction too. Requires
   care: presets currently let the user pick k independent of N0, and these
   two are physically related — coupling them removes a degree of freedom that
   some users may rely on.
2. **Opt-in "tie k-factor to N0" checkbox** *(MINOR — additive)*. Preserves
   today's independence while letting users opt into the coupling above.

Either change must update the user-facing docs to remove the implication that k
affects propagation directly.

#### Post-processing uses `QgsProject.instance()` instead of `context.project()`

Several post-processing and layer-load paths reach for the global project
singleton instead of the algorithm's context project:

- `base_algorithm.py:51` and `:68` — layer-tree reorder + `writeEntry`
- `processing_utils.py:47` — `queue_layer_for_loading` forces the layer into
  `QgsProject.instance()` via `LayerDetails(name, project, name)`
- `three_d.py:79,167`

`QgsProcessingContext` carries explicit thread/project affinity and exposes
`context.project()` — the project the algorithm is actually running against, and
the project `LayerDetails` loads completion layers into (per the
[QgsProcessingContext reference](https://qgis.org/pyqgis/master/core/QgsProcessingContext.html)).
`postProcessAlgorithm` "will always be called from the same thread that context
has thread affinity with… generally the main thread… not guaranteed"
([QgsProcessingAlgorithm reference](https://qgis.org/pyqgis/3.44/core/QgsProcessingAlgorithm.html)).

When the algorithm runs interactively from the plugin menu, `context.project()`
*is* the active project, so today's code works. It diverges in the **Model
Designer**, **batch processing**, and `processing.run()` headless contexts: the
layer-tree reorder runs on the singleton's root while layers loaded on
completion land in the context project (reorder finds nothing), and `writeEntry`
lands on the wrong project. `algorithm/contour.py:212,260` already uses
`context.project()` correctly — so the codebase is internally inconsistent.

**Fix:** thread `context.project()` through these paths, falling back to
`QgsProject.instance()` only when no context is available. No public signature
change; correctness in model/batch/headless contexts → PATCH.

### Robustness

#### Thread P2P and Contour off the main thread (and restore cancellability)

`P2PAlgorithm` and `ContourLinesAlgorithm` run with `NoThreading`
(`ALLOW_THREADING` unset → `False` in `base_algorithm.py:33`) while performing
network DEM/tile downloads and compute on the GUI thread. Per the QGIS API a
`NoThreading` algorithm is initialized with `QgsTask::Flag()` rather than
`QgsTask::CanCancel` — QGIS treats it as **non-cancellable by design** and does
not wire the dialog cancel button
([QGIS PR #9026](https://github.com/qgis/QGIS/pull/9026)). Consequences: the UI
freezes for the download duration, and the in-loop `feedback.isCanceled()`
checks in `tile_download_base.py` / `contour/pipeline.py` can never observe a
cancel from the dialog.

P2P cannot simply flip the flag: it builds the matplotlib chart
(`show_profile_chart`) and loads layers inside `processAlgorithm`, and GUI
objects must be created on the context's affinity thread. Since
`postProcessAlgorithm` runs on that thread (generally the main thread for
interactive runs), the rework is:

1. Keep the download/ITM/Fresnel compute in `processAlgorithm` (now threadable).
2. Move chart creation + `queue_layer_for_loading` into `postProcessAlgorithm`.
3. Put any thread-unsafe setup in `prepareAlgorithm` (runs on the main thread).
4. Set `ALLOW_THREADING = True` on both once the GUI work is relocated.

This restores a responsive, cancellable UI for the two network-bound
algorithms and pairs naturally with the `run_p2p_analysis` decomposition under
Decomposition. Output layers/reports are byte-identical (existing P2P/contour
contract and golden-file tests verify this) — only the execution thread changes.
Robustness, no public signature change → PATCH.

## Cleanups (PATCH)

### Decomposition

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

#### Document a reproducible local dev-environment bootstrap

The CI pipeline is the source of truth (`uv.lock` + `constraints-ci.txt` +
role-specific `requirements-*.txt`), but a hand-rolled local `.venv` drifts
from it silently. Observed failure mode: a venv whose `pytest` shebang resolved
to Python 3.11 while `.venv/bin/python` was 3.12, missing `hypothesis` and
`pytest-cov`, so a bare `pytest` collection-errored on the four
`tests/test_hypothesis_*.py` files with `ModuleNotFoundError: No module named
'hypothesis'` — looking like a repo breakage when it was purely an environment
mismatch.

Add a short "Local setup" stanza to `CONTRIBUTING.md` that pins one
interpreter and one install path — e.g. `uv sync` against `uv.lock`, or
`pip install -c constraints-ci.txt -r requirements-test.txt` into a single
fresh venv — and the exact `pytest -m "not qgis_integration and not
gdal_integration and not benchmark"` invocation the unit job uses. Docs only →
no version bump.

#### Add unit tests for `_compute_single_link` and `ElevationGrid`

Two pure-logic hotspots are reachable by the unit job (no QGIS runtime) but
under-covered:

- `batch/outputs.py::_compute_single_link` (~58%) — the repo's worst health
  biomarker. Mockable with a synthetic terrain profile plus a fake clutter
  context; tests would lock down the EIRP/`prx_dbm`/`margin_db`/`clearance_pct`
  math and the terminal-height out-of-range skip branches (`outputs.py:72-79`).
- `elevation.py::ElevationGrid` (~67%) — pure numpy. The uncovered south-up
  row-flip path (`elevation.py:130-144`) and the short-distance branch of
  `terrain_profile` (`elevation.py:190-191`) are exactly the edge logic that
  fails silently.

Both also widen the currently-thin coverage margin (66.9% unit vs. 64% gate).
Follow the `tests/test_dataclass_params.py` / `tests/_qgis_mocks.py` patterns;
pairs with the existing `batch/params.py` test entry above and the
`_compute_single_link` decomposition under Decomposition. Tests only → PATCH.

#### Clear the `pip-audit` job's pip-self noise

The `audit` job currently reports CVEs in `pip` itself (the build tool), not in
any shipped dependency — harmless, but it dirties the one job whose value is a
clean signal, so a real future CVE in a real dependency would hide in the
noise. Either upgrade pip in the audit venv before running
(`python -m pip install --upgrade pip`) or add an explicit, commented
`--ignore-vuln` for the pip-self advisories so genuine findings stand out.
CI tweak → PATCH.

#### Gitignore local-only tool config

`.mcp.json` (contains a hardcoded absolute path,
`/home/bortre/03-final/nowires_qgis_plugin`) and `provider_config.json` are
untracked developer-environment files — not in the release include-list, so no
shipping risk. But the absolute path in `.mcp.json` makes it non-portable if
ever shared, and either could be committed by accident. Decide intent: add both
to `.gitignore` to keep them explicitly local-only, or make `.mcp.json`'s path
relative if it is meant to be shared. Hygiene only → no version bump.

#### Provide in-dialog help on every algorithm

`shortHelpString()` is implemented only on `BatchAnalysisAlgorithm`
(`algorithm/batch.py:258`) and `CoverageComparisonAlgorithm`
(`algorithm/coverage_comparison.py:244`). P2P, Coverage, and Contour show an
empty help panel in their Processing dialogs. Add `shortHelpString()` — and
optionally `helpUrl()` deep-linking to the hosted `USERS-GUIDE.md` — to all
five, ideally a `NoWiresAlgorithm` base default plus per-algorithm overrides.
Both are standard `QgsProcessingAlgorithm` overrides
([reference](https://qgis.org/pyqgis/3.44/core/QgsProcessingAlgorithm.html)).
Additive help text, no behavior change → PATCH.

#### Brand each algorithm with `icon()`

`NoWiresProvider.icon()` (`provider.py:79`) sets the toolbox group icon, but the
algorithms themselves define no `icon()`, so each shows the default gear in the
Processing toolbox. Add a one-line `icon()` on `NoWiresAlgorithm` reusing
`logo.png`. Cosmetic → PATCH.

#### Decide and document the `qgisMinimumVersion` floor

`metadata.txt` sets `qgisMinimumVersion=4.0` / `qgisMaximumVersion=4.99`. QGIS
4.0 (Qt6) shipped February 2026, but the first 4.x LTR is **4.2, not due until
October 2026** ([QGIS.org blog](https://blog.qgis.org/2025/10/07/update-on-qgis-4-0-release-schedule-and-ltr-plans/)),
so until then the conservative/institutional base remains on the 3.x series
(3.40 LTR), excluded by this floor. QGIS 4.0 is a hard Qt5→Qt6 break, so
spanning both from one codebase is real work if any Qt6-only or PyQGIS-4-only
API is used.

**Decision needed:** either keep the 4.0-only floor and document the rationale
in `README.md` (riding the Qt6 line, awaiting the 4.2 LTR), or audit the code
for Qt6/PyQGIS-4-only API usage and lower the floor to a 3.x LTR to widen reach.
The code already uses the `qgis.PyQt` shim and the scoped Qt6 enum
`Qgis.ProcessingAlgorithmFlag.NoThreading` (`base_algorithm.py:38`), which is
correct for 4.0. No code change unless the floor is lowered → docs/metadata.

## Performance (PATCH)

#### Speed up coverage compute: compile the ITM core

Coverage generation time is dominated by the per-pixel ITM computation, not by
the QGIS plumbing. `radio_coverage/_executor.py` maps pixel chunks across a
`ProcessPoolExecutor`; each task samples a terrain line and runs the pure-Python
Longley–Rice port in `itm/` (`compute_itm_p2p` →
`itm/propagation.py`, `itm/variability.py`, `itm/terrain.py`). The interpreted
inner loop is the bottleneck; the surrounding multiprocessing, chunking
(`_dynamic_chunk_size`), and shared-memory grid are already efficient.

**Measured baseline (don't assume — this was profiled).** A microbenchmark of
`predict_p2p` on a representative 101-sample profile (CPython 3.12, best-of-N):
interpreted ≈ **76 µs/call**, mypyc-compiled with zero source changes ≈
**66 µs/call** — only **~1.15× (≈15%)**, *not* the 2–4× mypyc rule-of-thumb.
A `cProfile` breakdown shows why: the per-call time is dominated by functions
running **numpy on tiny (101-element) arrays** — `compute_delta_h` alone is
~23% of total time, plus `linear_least_squares_fit`, `find_horizons`,
`smooth_earth_diffraction`. mypyc removes interpreter/dispatch overhead from the
scalar arithmetic but **cannot speed up the numpy calls**, and on arrays this
small the numpy per-call overhead (array setup, scalar boxing) dominates the
actual math. So bare compilation of the code *as written* hits a ~15% ceiling,
and because per-pixel work also includes terrain sampling, antenna/clutter, and
multiprocessing/IPC, the whole-coverage gain is single-digit percent. The
compile itself was clean: all 7 modules built to `.so`, output bit-identical.

Three approaches below, ordered by ceiling. All behavior-preserving. In every case, keep a **pure-Python
fallback** so the plugin still loads where a compiled artifact isn't available
— the bundled-plugin install model can't assume a C toolchain on the user's
machine — and gate the bundling/packaging decision in `release.yml` accordingly.

**Option A — bind to the NTIA/itm C++ reference (fastest, most authoritative).**
The bundled `itm/` is a pure-Python port whose documented upstream is the NTIA
ITM C++ implementation (see `NOTICE.md`: NTIA/itm → tedaks/itm → tedaks/pyitm).
That reference exposes a clean `extern "C"` ABI — `ITM_P2P_TLS(h_tx, h_rx,
pfl[], climate, N_0, f__mhz, pol, epsilon, sigma, mdvar, time, location,
situation, &A__db, &warnings)` is exactly the per-pixel call NoWires makes — so
a **ctypes/cffi binding needs no pybind11**. License is clean: NTIA works are
US-Government public domain with an explicit worldwide derivative/redistribution
grant (already acknowledged in `NOTICE.md`), GPL-compatible. Native C++ is the
biggest available speedup precisely because it sidesteps the bottleneck found
above: the reference does this math as scalar `double` loops with **no numpy
boundary**, so it has none of the small-array overhead that caps the mypyc path
at ~15%. The reference also ships its own validation vectors (`p2p.csv`,
`area.csv`, `pfls.csv`) so results match the canonical model by construction.

*Caveats:* the upstream header guards exports with `__declspec(dllexport)`
(Windows-only) — a cross-platform build needs an export-macro guard for
gcc/clang `.so`/`.dylib`. And shipping native code means a **per-platform/arch
prebuilt-binary matrix** in `release.yml` (or an opt-in download), heavier than
Option B. This adds a build dependency the project does not currently have.

**Option B — mypyc-compile the existing Python port as-is (lowest effort, ~15%).**
`itm/` compiles cleanly with zero source changes (verified: all 7 modules → `.so`,
bit-identical output), keeps one implementation (no FFI, no second language), and
`mypyc` is already in the toolchain. But the **measured gain is only ~1.15×**
(see baseline above) because the numpy-on-small-arrays hot spots are untouched,
and it still needs per-platform, per-Python-version compiled wheels (mypyc output
is tied to the CPython ABI — narrower than Option A's version-independent C ABI).
Low effort, low ceiling — worth it only if a clean ~15% with a trivial build step
is judged sufficient.

**Option C — de-numpy the hot spots, then mypyc-compile (higher ceiling, no FFI).**
The reason Option B caps at ~15% is numpy overhead on 101-element arrays. Rewrite
the small-array hot functions — `compute_delta_h` (`itm/terrain.py:73`, ~23% of
per-call time), `linear_least_squares_fit` (`itm/variability.py:83`),
`find_horizons`, `smooth_earth_diffraction` — as **pure scalar Python loops** over
the profile (no `np.sum`/`np.dot`/`np.std` on tiny arrays). Interpreted, that may
be a wash or slightly slower; **compiled with mypyc it is the sweet spot** — a
scalar C loop beats numpy's per-call overhead at this size, plausibly reaching the
2–4× range without leaving Python or taking on a native-binary matrix. This is a
real refactor of numeric code, so the bit-stability gate below is mandatory and
the risk is higher than Option B. Best value-to-risk if the benchmark (below)
confirms the ITM loop dominates whole-coverage wall-clock.

**Hard correctness gate (all options):** numeric output must stay bit-stable.
`tests/test_itm_reference_vectors.py` + `tests/test_itm_reference_smoke.py` are
the gate — most critical for Option C, where numeric code is actually rewritten
(not just recompiled). Note a subtlety for Option A: C++ floating-point (libm, FMA, compiler
flags) may differ from the Python port in the last bits, so validate the binding
against the NTIA reference CSVs and decide an explicit tolerance — the C++ lib is
the *more* authoritative reference, so any divergence is the port's, not the
lib's.

**Secondary levers (separate, larger efforts):**

- **Worker/chunk tuning** — `NOWIRES_MAX_WORKERS` and `_dynamic_chunk_size` are
  already reasonable; profile before touching.
- **Shared terrain-profile reuse** — adjacent pixels resample overlapping DEM
  lines from the same TX; a per-run profile cache could cut redundant sampling,
  but it is a real design change with its own correctness surface. Scope
  separately.

**Sequencing:** benchmark first. `benchmarks/` and
`tests/test_coverage_engine_perf.py` already exist — capture a baseline
coverage-run profile to confirm the ITM loop is the dominant cost before
investing in the compile/packaging work, then re-measure to quantify the gain.

A behavior-identical compiled build is a zero-behavior-change optimization →
PATCH (per AGENTS.md). If compilation is shipped as an optional build artifact
rather than always-on, the packaging change still stays PATCH since runtime
behavior and the public API are unchanged.

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

### Best-server / multi-site composite coverage

The single largest functional gap for anyone planning more than one
transmitter. Forsk Atoll, ATDI ICS Telecom, Radio Mobile (network mode) and
CloudRF all compute, per pixel, *which* of N sites serves best. NoWires already
produces a single-TX `CoverageResult` (`radio_coverage/pool.py`) holding
`prx_grid` / `loss_grid` over a shared lat/lon grid — this feature stacks N such
runs onto a common grid and reduces across the stack.

**New algorithm** (`algorithm/best_server.py`, registered in `provider.py`)
taking a point layer of transmitters (reuse the Batch candidate-TX ingestion in
`batch/params.py`) and emitting:

- **Best-server raster** — per pixel, the index of the strongest TX (categorized
  raster + matching legend, reuse `radio_coverage/legend.py`).
- **Max-RSSI raster** — per pixel, the strongest received power across all sites
  (feeds straight into the existing coverage palette/opacity styling).
- **Overlap / handoff raster** — count of sites above threshold per pixel, or the
  margin between best and second-best server (handoff zones).

Implementation reuses `compute_coverage` per site onto one pre-allocated grid;
the reduction is an `np.argmax` / `np.maximum.reduce` pass. Per-site runs are
already parallelized internally, so the outer loop stays sequential.
Cancellation and progress thread through the existing feedback object.

New processing algorithm → MINOR. Brainstorm the TX-layer schema (per-site
power/height/antenna overrides) before code; manual QGIS UI test required.

### ITU-R P.530 microwave link availability (rain + multipath)

`reliability.py:27-72` exposes an availability percentage explicitly disclaimed
as "a heuristic blend ... NOT an ITU-R P.530 calculation." This is the core
workflow of Pathloss 5/6 and the headline number microwave/backhaul engineers
sign off on. Replace the heuristic with a genuine P.530 chain:

- **Multipath outage** — P.530 §2.3 (geoclimatic factor, path inclination, fade
  depth → outage probability).
- **Rain attenuation** — P.838 specific attenuation γ_R from frequency,
  polarization and rain rate; P.837 rain-rate R₀.₀₁ at the path location; P.530
  effective-path-length reduction → attenuation exceeded for 0.01% of time, then
  scaled to the target availability.
- **Combined availability** and the inverse solve: *fade margin required for a
  target availability* (the "five nines" design question).

Lands in `reliability.py` plus a small `p530.py`; pure math, well-specified by
the ITU recommendations. Only new data dependency is the ITU-R P.837 rain-rate
global grid — bundle the coarse grid or fetch on demand through the existing
tile-download/cache machinery (`tile_download_base.py`). Surface the result in
the P2P and Batch reports next to the existing availability fields
(`radio_coverage/reporting.py:189-206`).

Replaces a public heuristic with a real calculation and adds report fields →
MINOR. Keep the heuristic reachable behind a flag during transition; golden-file
report tests must be updated, not silently broken.

### Manufacturer antenna-pattern import (NSMA / MSI) and 3D patterns

`antenna.py:150 _read_pattern_points` reads a custom azimuth-only CSV. Pro tools
ingest real vendor files and model the full sphere. Add:

- **Parsers for NSMA (`.adf`) and Planet/MSI (`.msi`)** pattern files alongside
  the existing CSV reader, sharing the session cache and the
  `MAX_PATTERN_ROWS` guard already in `antenna.py`.
- **Elevation-plane support and 3D synthesis** — accept horizontal *and*
  vertical cuts and synthesize a 3D gain via cross-weighted interpolation
  (e.g., the Gain = f(H, V) bilinear-on-the-sphere method), so azimuth *and*
  electrical/mechanical downtilt are modeled correctly rather than approximated
  by the current preset front/back + downtilt scalars.
- Extend `antenna_pattern_preview.py` to render the vertical cut / 3D pattern so
  non-RF users can still sanity-check the file.

Big accuracy win for sectorized sites; fully contained in `antenna.py` and the
preview dialog. New file formats + elevation dimension are additive → MINOR.
Verify `antenna_gain_adjustment_db` callers (P2P, Batch, Coverage) feed the
elevation angle they already compute (`vertical_angle` in `p2p/compute.py:170`).

### Coverage statistics, served-area polygons, and KMZ export

Three small, high-leverage outputs every professional tool ships, all built on
grids NoWires already computes:

- **Threshold statistics** — % of analysis area above each signal threshold (and
  % population if the user supplies a population raster), written into the
  coverage report (`radio_coverage/reporting.py`).
- **Served-area vector polygons** — polygonize the coverage raster at one or more
  thresholds (GDAL `Polygonize`) into a styled vector layer, so coverage can be
  intersected with other GIS data.
- **KML / KMZ export** — coverage raster → coloured ground-overlay KMZ and the
  P2P path/profile → KML, for Google Earth sharing (a CloudRF / Radio Mobile
  staple). One-click export of the same data already loaded into QGIS.

Low effort, high visibility; mostly additive output parameters on existing
algorithms → MINOR. The served-area and statistics passes are pure numpy/GDAL
and unit-testable without a QGIS runtime.

### Diffraction-loss obstruction breakdown (diagnostic)

ITM already accounts for diffraction in the predicted loss, but Pathloss and
Radio Mobile show the *diagnostic*: per-obstacle knife-edge loss
(Deygout / Bullington / Epstein-Peterson), which ridge dominates, and individual
clearances. Add a diffraction breakdown to the P2P profile chart and report —
explanatory depth that does **not** change the predicted loss number (the ITM
result stays authoritative). Reuses the terrain profile and Fresnel geometry
already in `fresnel.py` / `p2p/compute.py`. Additive report/chart content →
MINOR.

### ITU-R P.1812 as an alternative point-to-area model (longer horizon)

A second propagation engine lets users cross-check ITM against the modern
European terrestrial/broadcast model (30 MHz – 6 GHz, location-percentage
based, widely used for DTT planning). Would live beside `itm/` as an isolated
pure-computation package (same `import-linter` "no qgis" contract as `itm/`) and
be selectable per algorithm.

**Heavy:** P.1812 pulls in P.526 diffraction, clutter handling, and troposcatter
— a substantial implementation effort. Lower priority than the items above
precisely because ITM already covers the core niche. New model + selector →
MINOR, but scope a full spec before committing.

### ITU-R P.452 interference / coordination contours (longer horizon)

The other half of network planning: carrier-to-interference C/(I+N) between a
victim and one or more interferers, and coordination contours for spectrum
sharing. High value for shared-spectrum and licensing work, but P.452 is a large
model in its own right. Treat as a separate epic after P.1812 establishes the
multi-model pattern. New algorithm + model → MINOR.
