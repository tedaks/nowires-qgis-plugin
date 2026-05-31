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

Releases are grouped by next version number; within each, items are ordered by
the AGENTS.md release shape convention (security → leaks → correctness →
robustness → dead-code cleanup → decomposition → polish → features). Each
item includes its regression test specification per the TDD convention
(§Regression Test Naming Convention).

---

## v1.7.1 — PATCH: bugfixes and dead-code cleanup ✅ Shipped 2026-05-30

All items below have landed and moved to CHANGELOG.md. Kept for historical
reference; see CHANGELOG.md §[1.7.1] for the shipped entries.

Bug fixes ordered security → leaks → correctness → robustness, then
dead-code cleanup. Each fix lands with a named regression test that fails
without the patch.

### Correctness

#### Post-processing uses `QgsProject.instance()` instead of `context.project()` ✅

Fixed in v1.7.1. `base_algorithm.py`, `contour.py` `postProcessAlgorithm`, and
`processing_utils.queue_layer_for_loading` now use `context.project()` with
fallback to `QgsProject.instance()`. `three_d.py` functions accept an optional
`project` parameter.

Regression test: `test_project_context_layer_placement.py`

#### K-factor threading: batch `itm_p2p_loss` missing `k_factor` ✅

Fixed in v1.7.1. `batch/outputs.py:_compute_single_link` now forwards
`k_factor=params.k_factor` to `itm_p2p_loss`.

Regression test: `test_batch_k_factor_forwarding.py`

### Robustness

#### Thread P2P and Contour off the main thread (and restore cancellability) ✅

Fixed in v1.7.1. Both `P2PAlgorithm` and `ContourLinesAlgorithm` now set
`ALLOW_THREADING = True`. Chart creation (`show_profile_chart`) is deferred
to `postProcessAlgorithm` which runs on the context's affinity thread.

Regression tests: `test_p2p_contour_threading.py`, `test_algorithm_threading_optin.py`

#### Fail-fast input validation before DEM download ✅

Fixed in v1.7.1. `validate_itm_input_ranges` now validates time/location/situation
percentages, k-factor, and epsilon in addition to the existing checks.
Coverage algorithm now calls `validate_itm_input_ranges` before
`ensure_dem_for_area`.

Regression tests: `test_fail_fast_input_validation.py`, `test_coverage_validate_before_dem.py`

#### Pre-run AOI + download-size summary ✅

Fixed in v1.7.1. `ensure_dem_for_area` pushes a summary message with AOI
dimensions, tile count, estimated size, and pixel count before downloading.

Regression test: `test_aoi_feedback_summary.py`

### Cleanups

#### K-factor parameter: remaining open options ✅ Resolved in v2.0.0

The interim label-clarification shipped in v1.7.0. Both full fixes have now
landed together in v2.0.0: option 1 (preset→N0 coupling, MAJOR default change)
and option 2 (the opt-in `DECOUPLE_N0` checkbox, MINOR). See the v2.0.0 entry
above.

---

## v2.0.0 — MAJOR: saalos replacement and k-factor N0 coupling

This release ships immediately after v1.7.1, prioritised by licence risk. The
saalos → P.833-9 §2.1 replacement removes `clutter_loss_saalos` and
`clutter_loss_saalos_vec` from the public API and changes the default numeric
output for the vegetation clutter category (removed symbols + default change →
MAJOR). The k-factor N0 coupling (option 1) is bundled here if chosen; option 2
(opt-in checkbox) is MINOR and targets v2.1.0+.

### Replace saalos vegetation model with ITU-R P.833-9 §2.1 (default change)  ✅ Shipped in v2.0.0

Removes `clutter/saalos.py`, `clutter/_saalos_vec.py`, `MAX_CLUTTER_LOSS` from
`clutter/constants.py`, three dead `ClutterLossContext` fields (`polarization`,
`rx_ground_elevation_m`, `tx_ground_elevation_m`), `_build_rx_ground_grid` from
`radio_coverage/engine.py`, and six saalos-specific test files. Replaces with
`clutter/p833.py` implementing Am from P.833-9 §2.1 Equation 2
(`Am = A1 · f^α`, St. Petersburg fit A1=1.37, α=0.42).

**Numeric change:** saalos was frequency-independent in practice — it always
returned `MAX_CLUTTER_LOSS = 22 dB` at any practical link distance. P.833-9 Am
is frequency-dependent: 17 dB at 450 MHz, 23 dB at 900 MHz, 31 dB at 1800 MHz,
37 dB at 2600 MHz. Users below ~850 MHz see less vegetation loss; users above
1 GHz see more.

**Pipeline clean-up included:** removing `_build_rx_ground_grid` eliminates an
O(grid²) DEM sample pass from advanced-mode coverage analysis; removing the
three dead context fields simplifies per-pixel context construction in
`radio_coverage/tasks.py`.
Golden-file tests for the vegetation clutter category must be re-baselined.

### K-factor preset coupled to N0 (default change)  ✅ Shipped in v2.0.0

Each `K_FACTOR_PRESET` now maps to a representative N0 (0.67→250, 1.00→280,
1.33→301, 2.00→350, 4.00→400 N-units; full-range spread) so changing the preset
changes the ITM propagation prediction, not only the Fresnel/LOS display. The
standard 1.33 preset is pinned to `DEFAULT_N0=301`, so default-preset runs are
numerically unchanged. The mapping and resolvers live in the new
`k_factor_presets.py` (`K_FACTOR_PRESET_N0`, `resolve_n0`), re-exported from
`radio`. Coupling is applied in the P2P and Batch algorithm readers, which push
a feedback note when the preset overrides the user's N0.

Both options landed together: option 1 (coupling, MAJOR — default change) and
option 2 (the opt-in `DECOUPLE_N0` checkbox, MINOR) so users who need k
independent of N0 can still work. The Custom preset also leaves N0 free.

**Regression tests (landed):**
- `test_k_factor_n0_coupling.py` — verifies the coupled N0 for each preset, the
  Custom-preset pass-through, and that the coupled N0 changes ITM loss.
- `test_k_factor_preset_backward_compat.py` — verifies the `DECOUPLE_N0`
  checkbox restores the old behavior (preset affects Fresnel only, N0 stays as
  entered) and that the control is wired through P2P/Batch.
- Golden-file report tests are unaffected: they exercise the report writers
  with fixed payloads, not the algorithm readers where coupling happens, and
  the default-preset path is byte-identical. No re-baseline was needed.

---

## v2.1.0 — MINOR: dataclass migration, proxy auth, UX polish, and cleanups

This release batches the dataclass migration (prerequisite for deeper
decompositions), proxy auth, and several high-impact UX/robustness items.
PATCH-level cleanups and decompositions may be bundled under this MINOR bump.

### Bug fixes (PATCH — bundled in this release)

#### Group each run's outputs into a named layer-tree group

No `QgsLayerTreeGroup` usage exists anywhere. A coverage or P2P run drops 3–6
loose layers (raster + markers + Fresnel + legend …) flat into the layer panel,
and repeated runs pile up unmanageably. In `postProcessAlgorithm` (which already
manipulates the layer tree — see the `context.project()` correctness fix above)
create or find a named group like `"NoWires — Coverage 900 MHz 50 km"` and move
the run's output nodes into it. Use `context.project()`, not the singleton.

Visible behavior change (output placement), no new parameter → PATCH. Highest
daily-ergonomics win for the least code.

**Regression tests:**
- `test_layer_tree_group_naming.py` — unit test for the group naming function
  (algorithm name + frequency + radius template).
- `qgis_integration`-marked test: run a P2P algorithm in the QGIS container and
  verify the output layer-tree contains a named group with all output layers
  inside it.

#### Clickable "open report" pointer after a run

HTML/PDF/CSV reports are declared file outputs, but nothing points the user at
them. Push a clickable `file://` path via `feedback` (and `QDesktopServices.openUrl`
in the menu-driven flows) so the report opens in one click rather than being
hunted down. Wire near `algorithm/_coverage_helpers.py:160` and the P2P report
write in `p2p/compute.py`. Polish → PATCH.

**Regression test:** `test_open_report_pointer.py` — after a P2P/coverage
algorithm run in the QGIS integration container, assert `feedback.pushInfo`
was called with a `file://` URI pointing at the generated HTML report.

#### Result summary in the QGIS message bar with a "View report" action

Completion feedback currently lives only in the Processing log. After a run,
push a one-line summary to `iface.messageBar()` (e.g. "Coverage: 62% above
sensitivity · 4 tiles · 12 s") with an inline action button that opens the HTML
report — far more visible than log text, and the message-bar-native companion to
the "open report" pointer above. The menu-driven launchers in `nowires.py`
already hold an `iface` reference; thread a concise summary back from the
algorithm result. Feedback/UX only → PATCH.

**Regression test:** `test_message_bar_summary.py` — mock `iface.messageBar()`;
assert the summary string contains percentage, tile count, and elapsed time.

#### Progress ETA / throughput in long runs

Coverage and Batch already call `feedback.setProgress`, but give no sense of how
long a run will take. Add a throughput (pixels/sec) and estimated-time-remaining
line to the periodic progress update in `radio_coverage/_executor.py` and
`batch/outputs.py`. Feedback only → PATCH.

**Regression test:** `test_progress_eta_feedback.py` — mock `feedback` and run
a small synthetic coverage; assert `pushInfo` was called with a message
containing both throughput (pixels/sec) and ETA.

#### Persist custom-dialog geometry/state

The custom `QDialog`s (`AntennaPatternPreviewDialog` in
`antenna_pattern_preview.py`, `CoverageOpacityDialog` in
`radio_coverage/opacity.py`) open at a default size/position every time.
Save/restore via `QSettings` on show/close so they reopen where the user left
them. Touch carefully: this is the same custom-Qt layer where dialog-lifecycle
leaks have occurred — the existing `destroyed.connect(...)` ref-nulling in
`nowires.py` must be preserved. Polish → PATCH.

**Regression test:** `test_dialog_geometry_persistence.py` — mock `QSettings`;
assert the dialog writes geometry on close and reads it on show. Verify the
`destroyed` signal ref-nulling is preserved (existing
`test_pattern_preview_dialog_leak.py` covers the lifecycle).

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

**Regression test:** `test_algorithm_help_strings.py` — iterate all registered
`NoWiresAlgorithm` subclasses; assert each returns a non-empty
`shortHelpString()`. Assert the string contains the algorithm display name.

#### Brand each algorithm with `icon()`

`NoWiresProvider.icon()` (`provider.py:79`) sets the toolbox group icon, but the
algorithms themselves define no `icon()`, so each shows the default gear in the
Processing toolbox. Add a one-line `icon()` on `NoWiresAlgorithm` reusing
`logo.png`. Cosmetic → PATCH.

**Regression test:** `test_algorithm_icon.py` — assert each registered
`NoWiresAlgorithm` subclass returns a non-null `QIcon` from `icon()`.

#### Clear the `pip-audit` job's pip-self noise

The `audit` job currently reports CVEs in `pip` itself (the build tool), not in
any shipped dependency — harmless, but it dirties the one job whose value is a
clean signal, so a real future CVE in a real dependency would hide in the
noise. Either upgrade pip in the audit venv before running
(`python -m pip install --upgrade pip`) or add an explicit, commented
`--ignore-vuln` for the pip-self advisories so genuine findings stand out.
CI tweak → PATCH.

**Regression test:** no code test needed; CI job output is the gate. Verify the
audit job output shows no pip-self advisories after the fix.

#### Gitignore local-only tool config

`.mcp.json` (contains a hardcoded absolute path,
`/home/bortre/03-final/nowires_qgis_plugin`) and `provider_config.json` are
untracked developer-environment files — not in the release include-list, so no
shipping risk. But the absolute path in `.mcp.json` makes it non-portable if
ever shared, and either could be committed by accident. Decide intent: add both
to `.gitignore` to keep them explicitly local-only, or make `.mcp.json`'s path
relative if it is meant to be shared. Hygiene only → no version bump.

**Regression test:** no code test needed; verify `.gitignore` contains the
entries and `git status --ignored` confirms they are ignored.

### Cleanups (PATCH — bundled in this release)

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

**Regression tests:** golden-file tests
(`tests/test_report_export_golden.py`) must produce byte-identical output. Add:
- `test_download_serve_from_cache.py` — unit tests for cache-hit/miss/verify paths.
- `test_http_error_classification.py` — parametrized tests for 404, 408, 425, 429,
  5xx, and unknown status codes, verifying correct action/retry-delay dispatch.

#### Add unit tests for `batch/params.py`

`batch/params.py` is a heavily depended-on module (16 dependents) with no
focused unit tests of its own. It is referenced by
`tests/test_batch_writer.py` and `tests/_qgis_mocks.py`, but those exercise
it incidentally rather than locking down its behavior.

Follow the `tests/test_dataclass_params.py` pattern that exists for
`CoverageAnalysisParams`. Cover: validation branches, default values,
parameter-registration order, QGIS-parameter to dataclass extraction.
Unit-testable with `tests/_qgis_mocks.py` — no QGIS runtime required.
Expect ~80 test LOC. Tests only → PATCH.

**Regression test:** `test_batch_params.py` — new file covering validation
branches, default values, parameter-registration order, QGIS-parameter to
dataclass extraction.

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

**Regression tests:**
- `test_compute_single_link_edges.py` — parametrized EIRP/`prx_dbm`/`margin_db`
  assertions; terminal-height out-of-range skip path.
- `test_elevation_south_up_flip.py` — south-up DEM flip path produces a
  contiguous array with correct values; short-distance `terrain_profile` edge
  case.

#### Add type hints to `antenna.py`, `nowires.py`, and `radio.py`

These three core modules have the highest concentration of untyped function
arguments. The rest of the codebase is well-typed. Closing this gap would enable
`mypy --strict` on the full project. Pure refactor → PATCH.

**Regression test:** `mypy --strict` passes with no errors on these three
modules. No new runtime tests needed; typecheck is the gate.

#### Document NoWires package-name requirement

`__init__.py:74` does `from NoWires.nowires import NoWiresPlugin` and every other
module uses `from NoWires.*` imports. The plugin install directory must be exactly
`NoWires` for any import to resolve — a clone into `nowires_qgis_plugin/` or any
QGIS-manager slug other than `NoWires` breaks the plugin. Either document the
requirement in README/INSTALL or convert to package-relative imports. Docs only →
no version bump.

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

### Features (MINOR — this release's new functionality)

#### Migrate high-arity functions to dataclass parameters

**Priority: ship early in this release.** This migration is a prerequisite for
the `run_p2p_analysis` and `compute_coverage` decompositions planned for later
(v2.2.0 cleanups) — the 19-arg helper calls block meaningful slicing. It also
stands alone as a robustness win (call-site fragility).

Two functions still take 19 positional/keyword arguments, well past the point
where call sites become fragile to argument-order mistakes. The dataclass
infrastructure already exists (`radio_coverage/analysis_params.py`,
`p2p/analysis_params.py`).

> Earlier phases of this migration have already landed:
> `build_coverage_report_payload_for_grid` (`radio_coverage/reporting.py`) now
> takes `(grids: CoverageGrids, params: CoverageAnalysisParams, …)` — ~5 args
> down from 34 — and `_write_p2p_output_layers` (`p2p/outputs_internal.py`)
> already accepts a `P2PAnalysisParams` object. The two functions below are
> what remains.

**`show_profile_chart` (`p2p/chart.py`), `compute_itm_p2p`
(`radio_coverage/compute.py`) — 19 each.** Most parameters already live in
`P2PAnalysisParams`. Pass the params object plus function-specific outputs
(file paths, computed arrays).

Migrate one function at a time; each migration is mechanical and
behavior-preserving. Update callers, then run the existing test suite — no new
tests needed since behavior does not change.

**Classification:** both functions are public — signature change escalates to
MINOR per AGENTS.md. One PR per function; feature PR per AGENTS.md release
shape.

Pre-flight: run `grep -r "from NoWires" -- ..` outside the plugin tree per
AGENTS.md; any external importer confirms the MINOR bump.

#### Proxy auth wired into all algorithms

`setup_proxy_opener` is called from `algorithm/contour.py:161` only. Coverage, P2P,
Batch, and Comparison invoke `ensure_dem_for_area` and `ensure_clutter_grid_for_area`
without any proxy, so users behind authenticated proxies cannot run those four
algorithms. Add `QgsProcessingParameterAuthConfig` to each, thread `proxy_opener`
through `ensure_dem_for_area` (already supported) and through
`ensure_worldcover_for_area` → `download_worldcover_tiles` (parameter needs adding).

Adds new processing parameters → MINOR. One PR.

**Regression tests:**
- `test_proxy_auth_all_algorithms.py` — for each algorithm class (P2P, Coverage,
  Batch, Comparison, Contour), assert that `QgsProcessingParameterAuthConfig` is
  present in the parameter list. For Contour, assert it already existed (not
  duplicated).
- `test_proxy_auth_threading.py` — assert `proxy_opener` is passed through to
  `ensure_dem_for_area` and `ensure_worldcover_for_area` in the four newly-wired
  algorithms. Mock the download functions and verify the opener is used.

#### Decide and document the `qgisMinimumVersion` floor

`metadata.txt` sets `qgisMinimumVersion=4.0` / `qgisMaximumVersion=4.99`. QGIS
4.0 (Qt6) shipped February 2026, but the first 4.x LTR is **4.2, not due until
October 2026** ([QGIS.org blog](https://blog.qgis.org/2025/10/07/update-on-qgis-4-0-release-schedule-and-ltr-plans/)),
so until then the conservative/institutional base remains on the 3.x series
(3.40 LTR), excluded by this floor. QGIS 4.0 is a hard Qt5→Qt6 break, so
spanning both from one codebase is real work if any Qt6-only or PyQGIS-4-only
API is used.

**Decision needed by v2.1.0 at the latest:** either keep the 4.0-only floor and
document the rationale in `README.md` (riding the Qt6 line, awaiting the 4.2 LTR),
or audit the code for Qt6/PyQGIS-4-only API usage and lower the floor to a 3.x LTR
to widen reach. Delaying past v2.1.0 risks a growing 3.x user base that cannot
install the plugin, and the decision informs whether the Export Portable Project
feature needs cross-version `.qgz` considerations.
The code already uses the `qgis.PyQt` shim and the scoped Qt6 enum
`Qgis.ProcessingAlgorithmFlag.NoThreading` (`base_algorithm.py:38`), which is
correct for 4.0. No code change unless the floor is lowered → docs/metadata.

**If the floor is lowered to 3.x:** this is a MINOR change (new users can
install). One PR: audit all `Qgis.` and `qgis.PyQt` shims for 3.x compat, set
`qgisMinimumVersion=3.40` in `metadata.txt`, document in `README.md`.

**Regression test:** `test_qgis_version_floor.py` — assert `metadata.txt`
`qgisMinimumVersion` matches the documented floor; if 3.x, assert no 4.0-only
API usage exists in the codebase.

---

## v2.2.0 — MINOR: decompositions, coverage UX, and P.530

Decompositions (pure refactor → PATCH) bundled with the P.530 feature (MINOR)
and coverage/palette UX (MINOR). The decompositions depend on the v2.1.0
dataclass migration landing first.

### Cleanups (PATCH — bundled in this release)

#### Decompose `run_p2p_analysis` into pipeline stages

**Depends on:** v2.1.0 dataclass migration (the 19-arg `_write_p2p_output_layers`
call becomes a one-liner once `P2PAnalysisParams` is passed).

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

All extracted helpers are underscore-prefixed (private); `run_p2p_analysis`
keeps its existing public signature. Pure refactor → PATCH.

**Regression tests:** existing golden-file tests must produce byte-identical
output. No new tests needed — decomposition preserves the public signature.

#### Decompose `compute_coverage` into pipeline stages

**Depends on:** v2.1.0 dataclass migration (the 30+ positional/keyword arguments
bundle into `CoverageAnalysisParams` first).

**Affected by v2.0.0:** `_build_rx_ground_grid` (lines 37–65) is removed in the
saalos replacement. Do not reference or split this function; it will not exist
when this decomposition lands.

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

`tests/test_coverage_engine.py` and `tests/test_coverage_engine_extended.py`
provide regression coverage; behavior must be byte-identical. Pure refactor
after the dataclass migration → PATCH.

**Regression tests:** existing `test_coverage_engine.py` /
`test_coverage_engine_extended.py` must produce byte-identical output.

#### Decompose remaining functions over 100 lines

Five functions still exceed the 100-line single-responsibility threshold after
the targeted decompositions above land:
`build_coverage_tasks()` (189), `show_profile_chart()` (172),
`add_panel_params()` (156), `_compute_single_link()` (145),
`write_fresnel_zone()` (117).
(`clutter_loss_saalos()` was also on this list but is removed entirely in v2.0.0.)

Each should split into 2-3 focused helpers per the 300-line file gate convention.
Behavior preserved by the existing golden-file tests.

**Regression tests:** golden-file tests byte-identical. Each decomposed function
gets 2-3 focused unit tests for the extracted helpers.

### Features (MINOR — this release's new functionality)

#### Reopenable P2P profile chart

Closing the P2P chart dock destroys the widget and drops all profile data —
the chart can only be recovered by re-running the algorithm. Store the last
`chart_kwargs` on the `show_profile_chart` module and add a "Reopen P2P Chart"
menu action so the graph is reopenable without recomputation.

**Regression test:** `test_p2p_chart_reopen.py` — after `show_profile_chart`
stores `chart_kwargs`, assert the "Reopen P2P Chart" action exists; assert that
reopening uses stored kwargs without recomputation; assert closing and reopening
produces the same visible chart data.

#### Selectable / colorblind-safe coverage palette

`radio_coverage/palette.py` hardwires one discrete pseudocolor ramp. Add a
palette-choice processing parameter offering the current ramp plus a
**viridis/colorblind-safe** option and a grayscale option (print/contrast).
Thread the choice through `apply_coverage_style` and the legend
(`radio_coverage/legend.py`) so the raster and its legend stay consistent.
Accessibility + print-quality win. New processing parameter → MINOR; keep the
current ramp as the default so existing projects render unchanged.

**Regression tests:**
- `test_palette_parameter_options.py` — assert the parameter offers exactly
  three options (default, viridis, grayscale); assert default renders
  byte-identical to current output.
- `test_palette_legend_consistency.py` — for each palette, assert the raster
  style and legend reference the same color ramp.

#### ITU-R P.530 microwave link availability (rain + multipath)

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

**Regression tests:**
- `test_p530_multipath_outage.py` — verify P.530 §2.3 calc against ITU reference
  examples (geoclimatic factor, path inclination, fade depth).
- `test_p530_rain_attenuation.py` — verify P.838 γ_R and P.837 R₀.₀₁ against
  ITU reference data sheets.
- `test_p530_combined_availability.py` — verify combined availability and
  inverse solve against known link budgets.
- Golden-file report tests must be updated (P.530 fields present, heuristic
  fields still present behind flag).

#### Embed run parameters as QGIS layer metadata

`scripts/package_gpkg.py` embeds rich metadata into its GPKG, but normal output
layers carry none. Write the run inputs (frequency, TX power, climate,
%time/location/situation, DEM/clutter source, plugin version) into
`QgsLayerMetadata` on each output raster/vector, so a layer is self-describing a
year later and the provenance travels inside the Export Portable Project bundle.
Additive enrichment with no new parameter or UI → MINOR (could be PATCH at
implementation time; decide then).

**Regression test:** `test_layer_metadata_provenance.py` — after a coverage or
P2P run in the `qgis_integration` container, assert each output layer's
`QgsLayerMetadata` contains frequency, TX power, plugin version, and DEM source
keywords.

---

## v2.3.0 — MINOR: best-server, export, antenna patterns

Three high-impact features that share the "new algorithm + new output" pattern.

### Features (MINOR)

#### Best-server / multi-site composite coverage

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

New processing algorithm → MINOR. Brainstorm the TX-layer schema before code;
manual QGIS UI test required.

**Regression tests:**
- `test_best_server_reduction.py` — unit tests for `np.argmax` /
  `np.maximum.reduce` reduction with synthetic multi-site grids (2–3 TX,
  tie-handling, all-below-threshold edge case).
- `test_best_server_legend.py` — golden-file test for the best-server legend
  output category mapping.
- `qgis_integration`-marked test: run a 2-TX best-server analysis and verify
  output rasters contain expected pixel values.

#### Manufacturer antenna-pattern import (NSMA / MSI) and 3D patterns

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

**Regression tests:**
- `test_nsma_adf_parser.py` — parse representative `.adf` files; assert gain
  values at cardinal angles match expectations; assert `MAX_PATTERN_ROWS` cap
  applies.
- `test_msi_parser.py` — parse representative `.msi` files; same checks.
- `test_antenna_3d_synthesis.py` — assert 3D gain interpolation returns
  azimuth-only gain when elevation is 0°; assert vertical-only pattern at
  azimuth 0°; assert pattern preview renders without error.
- Existing `test_antenna_patterns.py` must still pass (CSV import unchanged).

#### Export Portable Project (drop-and-open on any OS)

Results are portable today only if the user saves the project *before* running an
algorithm: `_project_or_temp_dir` (`algorithm/_project_paths.py`) writes outputs
to `<project_dir>/nowires_<name>/` when the project is saved, but falls back to
`/tmp/NoWires-<user>/…` otherwise — machine-local, user-specific, lost on reboot,
with absolute paths baked into the `.qgz`. There is no one-click way to bundle a
finished analysis for transfer to another PC/Mac/Linux machine. The one-off
`scripts/export_portable.py` and `scripts/package_gpkg.py` prove the recipe but
are hardcoded demos, not a feature.

Add an **"Export Portable Project"** processing algorithm that bundles every
NoWires layer + report into a chosen folder that opens unchanged on any OS:

- Copy all output rasters as **GeoTIFF Float32** (ideally COG: tiled + LZW/DEFLATE
  + internal overviews) — lossless for dBm/elevation, with CRS (EPSG:4326) and
  explicit NoData already embedded. **Do not** push rasters into a GeoPackage
  raster table: GPKG raster is a byte/PNG tile pyramid (see `package_gpkg.py`
  rescaling Float32 dBm → byte 0–250), which *loses* precision. GPKG raster is a
  display format, not lossless storage.
- Consolidate **vectors** (TX/RX markers, Fresnel, contours, boundaries) into one
  GeoPackage — lossless and portable, unlike Shapefile (10-char field
  truncation, multi-file).
- Write a **relative-path `.qgz`** (`writeEntry("Paths", "/Absolute", False)`)
  with NoWires **styles embedded**, plus optional `.qml` sidecars for QGIS↔QGIS
  fidelity (avoid SLD for the colour-ramp coverage style — lossy).
- Copy the CSV/JSON/HTML reports alongside, and optionally zip the folder.

**Bundled guardrail (robustness, PATCH on its own):** when an algorithm runs
against an **unsaved** project, push a clear `feedback.pushWarning` that outputs
are going to a machine-local temp dir and will not be portable until the project
is saved — `_project_or_temp_dir` already detects this case (empty
`context.project().fileName()`); it just needs to warn instead of silently
falling back to `/tmp`. Pairs naturally with also setting
`Paths/Absolute=False` on project write.

Caveats to document: a QGIS 4.0 (Qt6) `.qgz` may not open in 3.x (open on
same-or-newer QGIS); custom user-defined CRS and external SVG/fonts don't travel
(NoWires styling uses built-in renderers, so this is normally a non-issue).

New processing algorithm → MINOR; the unsaved-project warning is a small
robustness fix that can ship first. Brainstorm the output-folder/zip UX before
code. **Test gate:** manual QGIS round-trip test (export on Linux/macOS, open
on Windows + vice versa) recorded in the PR; add a `qgis_integration`-marked
test that verifies the produced `.qgz` references relative paths and that
output GeoTIFFs contain CRS + NoData. The unsaved-project warning must also
have a unit test (`feedback.pushWarning` spy).

**Regression tests:**
- `test_export_portable_relative_paths.py` — `qgis_integration`-marked; after
  export, parse the `.qgz` and assert `<Paths>/Absolute` is `False`.
- `test_export_portable_geotiff_crs.py` — `qgis_integration`-marked; assert
  output GeoTIFFs contain EPSG:4326 CRS and NoData value.
- `test_unsaved_project_warning.py` — mock `QgsProcessingContext` with empty
  filename; assert `feedback.pushWarning` was called.

#### Coverage statistics, served-area polygons, and KMZ export

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

**Regression tests:**
- `test_coverage_threshold_statistics.py` — synthetic grid; assert % above
  threshold matches hand-computed values.
- `test_served_area_polygonize.py` — synthetic grid; assert polygon count and
  area match expected.
- `test_kmz_export.py` — verify KMZ contains expected overlays; verify KML
  contains P2P path coordinates.

#### Diffraction-loss obstruction breakdown (diagnostic)

ITM already accounts for diffraction in the predicted loss, but Pathloss and
Radio Mobile show the *diagnostic*: per-obstacle knife-edge loss
(Deygout / Bullington / Epstein-Peterson), which ridge dominates, and individual
clearances. Add a diffraction breakdown to the P2P profile chart and report —
explanatory depth that does **not** change the predicted loss number (the ITM
result stays authoritative). Reuses the terrain profile and Fresnel geometry
already in `fresnel.py` / `p2p/compute.py`. Additive report/chart content →
MINOR.

**Regression tests:**
- `test_diffraction_breakdown.py` — synthetic terrain profile; assert
  obstruction identification and knife-edge loss match hand-computed Deygout
  values.
- Golden-file P2P report tests must show the new obstruction breakdown section.

---

## Backlog — longer-horizon items

Items not assigned to a specific release. Sequenced by dependency and impact.

### Performance

#### Speed up coverage compute: compile the ITM core

**Note:** v2.0.0 (saalos replacement) already removes `_build_rx_ground_grid`
from `radio_coverage/engine.py`, eliminating an O(grid²) DEM sample pass that
ran before every advanced-mode coverage analysis. That win ships before this
item; the bottleneck addressed here is the per-pixel ITM loop, which remains.

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

**Option A — bind to the NTIA/itm C++ reference (fastest, most authoritative).** *(MINOR — new native build dependency, per-platform binary matrix, and golden-test re-baseline.)*
The bundled `itm/` is a pure-Python port whose documented upstream is the NTIA
ITM C++ implementation (see `NOTICE.md`: NTIA/itm → tedaks/itm → tedaks/pyitm).
That reference exposes a clean `extern "C"` ABI — `ITM_P2P_TLS(h_tx, h_rx,
pfl[], climate, N_0, f__mhz, pol, epsilon, sigma, mdvar, time, location,
situation, &A__db, &warnings)` is exactly the per-pixel call NoWires makes — so
a **ctypes/cffi binding needs no pybind11**. License is clean: NTIA works are
US-Government public domain with an explicit worldwide derivative/redistribution
grant (already acknowledged in `NOTICE.md`), GPL-compatible. Native C++ sidesteps
the bottleneck found above — it does this math as scalar `double` loops with **no
numpy boundary** — so the ITM call itself runs far faster than either Python
path. The reference also ships its own validation vectors (`p2p.csv`, `area.csv`,
`pfls.csv`).

**Measured (Linux prototype, since removed).** A ctypes binding built from the
vendored NTIA source was benchmarked against the Python port:

- **ITM call alone: ~12×** (6.1 µs vs 74 µs/call), vs mypyc's ~1.15×.
- **End-to-end coverage compute: only ~3.1×.** ITM is just ~73% of per-pixel
  work (sampling, `build_pfl`, antenna, interpolation are the rest), so a 12× ITM
  gain collapses under Amdahl: `1 / (0.27 + 0.73/12.2) ≈ 3.0×`, matching the
  measured 3.10×. Total wall-clock is somewhat lower still after the
  multiprocessing/IPC overhead common to both backends.
- **Parity: bit-exact in 1194/1200 randomized cases.** The 6 divergences
  (≤ 1.66 dB) are confined to a 50 MHz / sub-km / few-sample edge regime and are
  the *port* deviating from the authoritative reference, not the binding — so
  adopting C++ would slightly *correct* the port there, but the reference-vector
  goldens would need re-baselining for those cases.
- **Next bottleneck:** once ITM is native, bilinear terrain sampling
  (`_bilinear.py`, ~16% of per-pixel time) dominates the remainder. Only the
  shared-profile-reuse lever below pushes past ~3×; the C++ ITM alone will not.

So the realistic payoff is **~3× compute** (less in wall-clock) for the full
per-platform native-binary matrix + maintenance cost — a measured trade-off, not
the headline 12×.

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

**Classification:** Option B and C produce zero-behavior-change optimizations →
PATCH (per AGENTS.md). Option A is **MINOR** because it adds a native build
dependency, a per-platform/arch binary matrix in `release.yml`, and re-baselines
the 6 divergent golden-test edge cases against the C++ reference — this is
additive packaging and test-surface work, not a pure optimization.

**Regression tests (per option):**
- All options: `test_itm_reference_vectors.py` and `test_itm_reference_smoke.py`
  must pass (Option A: re-baseline 6 divergent cases; Option B/C: byte-identical).
- Option A: add `test_itm_ctypes_binding.py` — verify ctypes binding loads,
  verify parity with Python port within tolerance (≤ 1.66 dB for the 6 known
  edge cases, exact for the rest).
- Option C: add `test_itm_scalar_hotspots.py` — compare de-numpified functions
  against numpy originals element-by-element on representative profiles.

#### P.1812 and P.452 propagation models

- **ITU-R P.1812 as an alternative point-to-area model** — a second propagation
  engine lets users cross-check ITM against the modern European
  terrestrial/broadcast model (30 MHz – 6 GHz, location-percentage based, widely
  used for DTT planning). Would live beside `itm/` as an isolated
  pure-computation package (same `import-linter` "no qgis" contract as `itm/`)
  and be selectable per algorithm. **Heavy:** P.1812 pulls in P.526 diffraction,
  clutter handling, and troposcatter — a substantial implementation effort.
  MINOR, but scope a full spec before committing.

- **ITU-R P.452 interference / coordination contours** — the other half of
  network planning: carrier-to-interference C/(I+N) between a victim and one or
  more interferers, and coordination contours for spectrum sharing. High value
  for shared-spectrum and licensing work, but P.452 is a large model in its own
  right. Treat as a separate epic after P.1812 establishes the multi-model
  pattern. New algorithm + model → MINOR.

**Regression tests:** each new model gets its own reference-vector test suite
mirroring `test_itm_reference_vectors.py`. P.1812: `test_p1812_reference_vectors.py`.
P.452: `test_p452_reference_vectors.py`.

### Features (MINOR — unscheduled)

#### Equipment presets (radio library)

Antenna presets exist (`ANTENNA_PRESETS`), but link-budget parameters —
frequency, TX power, RX sensitivity, cable loss — are entered raw every run. Add
a small JSON-backed library of named radio profiles
(e.g. "RF-7800V — 47 MHz, 10 W, −116 dBm") that populate those fields, editable
via a dialog (mirror the `antenna_pattern_preview.py` dialog lifecycle). Ship a
default library, allow user additions. Mirrors pro-tool equipment libraries and
cuts repetitive, error-prone entry; pairs with the portability theme. New
functionality + likely new parameters → MINOR.

**Regression tests:**
- `test_equipment_presets_load.py` — load default library; assert all presets have
  required fields; assert frequency/power/sensitivity values are valid.
- `test_equipment_presets_dialog.py` — `qgis_integration`-marked; verify dialog
  lifecycle (open, select, apply, close) without leaks.

#### Organize the plugin menu / add a NoWires dock panel

`nowires.py` adds nine flat entries to the Plugins menu (P2P, Coverage, Contour,
Opacity, 3D, Comparison, Batch, Pattern Preview, Clear Cache). Two options,
escalating:

1. **Submenu grouping** *(small, PATCH on its own)*: split into **Analysis ▸**
   (P2P/Coverage/Contour/Comparison/Batch), **Visualize ▸**
   (Opacity/Legend/3D/Pattern Preview), **Tools ▸** (Clear Cache). Pure menu
   wiring in `initGui`; declutters the Plugins menu.
2. **Dockable NoWires panel** *(MINOR)*: consolidate the visualize/tools actions
   into one `QgsDockWidget` so the post-run controls live next to the layers
   they act on, instead of being hunted in the Plugins menu. Adds custom-Qt
   surface (manual UI test before tagging); keep the menu actions too for
   discoverability.

Start with option 1 (cheap win); option 2 only if the panel earns its
maintenance cost.

**Regression tests (option 1):** `test_menu_subgroups.py` — assert each
algorithm's action is registered under the correct submenu (Analysis /
Visualize / Tools). **Regression tests (option 2):** `qgis_integration`-marked
test for dock widget lifecycle.

#### Live AOI / coverage-footprint preview on the canvas

Today the user types a TX point + radius and learns the actual area only *after*
the run (and the DEM download). Every professional tool shows the footprint as
it is set. Draw a **rubber-band preview** — a circle/extent on the map canvas
that updates as the TX point and radius change — so users see what they are
about to compute before committing. This pairs with the pre-run AOI/tile-size
summary (v1.7.1) and is the single biggest change to the plugin's feel.

This is the legitimate case for a **custom Processing parameter widget** (via
`createCustomParametersWidget` / a parameter widget wrapper) — the one thing the
plugin deliberately avoids today, since all current dialogs are framework-
generated — or a lightweight pre-run map tool launched from the menu. Higher
effort and it adds custom-Qt surface that CI can't validate
(`test_qt_widgets.py` is in the excluded `qgis_integration` set), so it needs a
manual QGIS UI test before tagging. New interactive UI → MINOR.

**Regression tests:** `test_aoi_preview_geometry.py` — unit test for the preview
geometry calculation (radius → canvas extent with CRS reprojection); the
custom-Qt widget itself must be manually tested in QGIS (not CI-validateable).