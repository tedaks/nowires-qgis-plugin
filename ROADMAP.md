# Roadmap

SPDX-License-Identifier: GPL-3.0-or-later

Planned work not yet implemented. Items move to [CHANGELOG.md](CHANGELOG.md) once landed.

## Planned for v1.6.7+

Carried forward from v1.6.5. Each has a verified root cause and a proposed fix in the sections below — ready to land.

### Docker QGIS integration tests for full algorithm orchestration

The Docker integration suite covers `algorithm/coverage.py` but lacks tests
for `algorithm/batch.py`, `algorithm/coverage_comparison.py`,
`algorithm/contour.py`, and `comparison/outputs.py`. These paths exercise
significantly different engine pathways and should be validated in the QGIS
Docker container against real Copernicus DEM tiles.

**Proposed fix.** Add `@pytest.mark.qgis_integration` test files for each
algorithm path, following the pattern of `test_qgis_integration.py`.

### Unit tests for legend.py

`radio_coverage/legend.py` legend data builders are Qt-dependent and currently
untested at the unit level. The legend construction logic (color stops, label
generation) can be tested in isolation with mocked Qt objects.

**Proposed fix.** Add unit tests covering `show_coverage_legend()` builder
functions with mocked `QgsRasterLayer` and `QgsSingleBandPseudoColorRenderer`.

### Coverage report.json omits most engine-consumed parameters (from v1.6.5)

`report/payloads.py:_build_coverage_input_dict()` serialises only 14 of the
26+ parameters consumed by the coverage engine. Missing fields include BEL,
clutter percentile, clutter overrides, antenna BW/AZ/downtilt, k-factor, N0,
epsilon, sigma. P2P reports echo most of these — the asymmetry is purely a
coverage-side gap.

The revised test harness compensated by externally capturing `params_sent.json`
before every `processAlgorithm()` call. Real users cannot do this — the
`report.json` is their only post-hoc evidence of what ran.

**Proposed fix.** Extend `_build_coverage_input_dict()` to mirror the P2P
inputs structure. Add a `clutter_model` field and a `clutter_advanced_active`
boolean to make mode-dependent param handling visible.

**Regression test.** `tests/test_coverage_report_includes_clutter_inputs.py` —
build a coverage payload with `bel_enabled=True, clutter_percentile=90.0,
tx_clutter_override="urban", downtilt_deg=6.0, k_factor=0.67`. Assert all five
appear under `inputs` in the resulting payload dict.

### GDAL geometry type warnings flood feedback logs (from v1.6.5)

Every coverage and P2P run emits 10–30 warnings: `"Layer 'markers' has been
declared with non-Z geometry type Point, but it does contain geometries with Z."`
These fill `feedback.log` with noise, making real warnings invisible.

**Proposed fix.** In each `ogr_driver.CreateLayer()` call across
`p2p/compute.py`, radio_coverage output paths, and comparison panel writers,
either set the geometry type to the Z variant (e.g., `wkbPoint25D` →
`wkbPointZM`) or suppress the warning with GDAL config.

### DEM download timeout on long cross-sea paths (from v1.6.5)

Manila → Cebu (~600 km) timed out at 300s inside `clips_and_merge_tiles →
ComputeStatistics`. The tile merger blocks indefinitely on GDAL operations
with no progress callback. Cross-sea paths download tiles with no land,
waste bandwidth, and stall the pipeline.

**Proposed fix.** Two-pronged:
1. Cap the DEM fetch to the land portion by intersecting the bounding
   box with a coastline proxy. Sea pixels don't contribute to ITM terrain.
2. Add a configurable timeout wrapping `ComputeStatistics` calls.

### Coverage polarization parameter has zero effect on output (new — 2026-05-26)

Surfaced by the revised test harness running against v1.6.5 HEAD (`run-4`,
QGIS 4.0 Docker). The behavioral assertion
`cov_pipeline_b_vs_cov_polar_v_manila` (varies only `POLARIZATION` between
horizontal and vertical, identical Manila 5 km path + 900 MHz + simple-clutter)
recorded `mean_dbm = -67.5` for both runs — **exact zero delta** against an
expected ≥ 0.2 dB threshold.

**Evidence.** From `run-3/cov_pipeline_b/analysis.json` and
`run-3/cov_polar_v_manila/analysis.json`:
```
mean_dbm: -67.5  (POLARIZATION=0, horizontal)
mean_dbm: -67.5  (POLARIZATION=1, vertical)
```

The P2P-side polarization assertion against the same Manila→Tagaytay path
produced a 0.022 dB delta (negligible but non-zero), which is consistent with
ITM polarization effects over rough land being small but real. The fact that
the coverage path returns *bit-equivalent* mean is suspicious — coverage either
isn't forwarding `polarization` to the engine, or is masking it via a
default-vertical short-circuit.

**Proposed investigation.** Trace `polarization` through
`radio_coverage/params.py` → `radio_coverage/engine.py` → `radio_coverage/tasks.py`
and verify it reaches the per-pixel ITM call. Compare with the P2P path
(`p2p/compute.py`) which does honor polarization (0.022 dB delta is below the
0.5 dB assertion threshold but the value is non-zero, proving the param does flow).

**Regression test.** `tests/test_coverage_honors_polarization.py` — run
`compute_coverage()` twice with `polarization=0` vs `polarization=1`, same TX
+ freq + power + grid + clutter. Assert the per-pixel `Prx` arrays differ
(not necessarily a large mean, but at least one cell ≥ 0.01 dB different).

### Coverage epsilon/sigma (ground material) has zero effect on output (new — 2026-05-26)

Same `run-4` harness run. The behavioral assertion
`cov_pipeline_b_vs_cov_ground_manila_seawater` varies `EPSILON` (15→70) and
`SIGMA` (0.005→5) — i.e. switching from default ground to seawater — over the
same Manila 5 km path. Recorded **exact zero delta**: `mean_dbm = -67.5` for both.

**Evidence.** From `run-3/cov_pipeline_b/analysis.json` and
`run-3/cov_ground_manila_seawater/analysis.json`:
```
mean_dbm: -67.5  (EPSILON=15, SIGMA=0.005 — default land)
mean_dbm: -67.5  (EPSILON=80, SIGMA=5 — seawater)
```

A two-decade change in conductivity and a ~5× change in permittivity should
produce a measurable difference even over a mostly-land path — the threshold
was set to ≥ 2 dB to be conservative. Zero delta suggests `epsilon`/`sigma`
are not flowing through to the ITM engine in the coverage path.

**Proposed investigation.** Same path as polarization above — trace through
`radio_coverage/params.py` → `engine.py` → `tasks.py`. Compare with P2P which
does include `epsilon`/`sigma` in `report.json` (the `inputs` block records
them; verify they're consumed not just echoed).

**Regression test.** `tests/test_coverage_honors_ground_material.py` — run
`compute_coverage()` twice with default ground vs seawater (epsilon=80, sigma=5),
same TX + freq + power + grid. Assert the per-pixel `Prx` arrays differ.

### BEL building type parameter has no effect on output (new — 2026-05-26)

v1.6.5 fixed BEL_ENABLED (BEL on/off produces 33 dB difference). However,
varying `BEL_BUILDING_TYPE` (0=tradiational suburban vs 1=residential urban
vs 2=commercial) at different elevation angles produces zero measurable
difference in coverage output. The P.2109 model should produce distinct losses
per building category and frequency.

**Proposed investigation.** Trace `bel_building_type` through
`clutter/p2109_bel.py` and verify the frequency-dependent loss table
distinguishes categories at 900 MHz. The BEL on/off path works; the
per-category differentiation may be masked or not implemented.

### DOWNTILT_DEG / ANTENNA_BW suppressed in coverage path (confirmed — 2026-05-26)

v1.6.5 fixed the comparison-side Omni preset override (forces BW=360, AZ=None
in `collect_panel_params()`). The coverage path (`radio_coverage/params.py`)
still preserves the custom BW/AZ when PRESET=0, but downstream discards them.
Two identical rasters are produced whether downtilt is 0° or 6°, or BW is 360°
or 65°.

**Proposed fix.** Apply the same normalization used in comparison params to
the coverage path: when `ANTENNA_PRESET=0` (Omni), force `antenna_bw_override=360.0`,
`antenna_az=None`, and `downtilt_deg=0.0` in `radio_coverage/params.py`.

### Test harness improvements

#### Test harness: no expects-error mechanism

`comprehensive-tests-v4.py:849-857` — any exception raised by an algorithm is
classified as FAIL. There is no allow-list for tests that intentionally exercise
guard rails.

**Evidence.** `edge_identical_points` (TX=RX, 0 m) is the single FAIL in the
v4 battery (56/57 passed). The plugin guard at `p2p/compute.py:89-92` correctly
rejects distances below `_MIN_P2P_DISTANCE_M=1.0 m` with a
`QgsProcessingException`. The test sends Manila→Manila expecting success and
the harness marks the resulting (correct) exception as FAIL.

**Proposed fix.** Add an optional `"expects_error"` key on test definitions
(string substring to match against the exception message). When present, the
runner classifies an exception containing the substring as PASS; absence of an
expected exception, or a different exception, is FAIL.

**Regression test.** Lives in the runner repository, not the plugin. Add an
`edge_zero_distance` test with
`"expects_error": "TX and RX points are too close"` and assert it appears in
the PASS column of `summary.csv`.

#### Test harness: noisy / duplicated warning thresholds

Two independent issues in `comprehensive-tests-v4.py` analyzers:

1. **Same-freq comparison warns "panels are identical"** even when the test
   declared `same_freq=True`. Line 771 fires unconditionally; the `same_freq`
   branch above only handles `mean_abs > 1.0`. Fix: change line 771 to
   `elif not same_freq and unchanged / max(total, 1) > 0.99 ...`.

2. **`itm < fspl - 0.5` and `excess < 0` both fire for the same condition**
   (lines 685 and 691). They detect the same underlying state. Keep only one,
   raise the threshold to `excess < -0.5` to match the other check's tolerance,
   and re-label as "enhanced propagation regime" rather than a warning — ITM
   can legitimately return loss below FSPL under low-percentile / enhanced-
   refraction conditions per NTIA TR-82-100.

Three of the seven warnings in v4 are rounding noise (`-0.0`, `-0.0`, `-0.1`
dB) that would be eliminated by tightening the threshold.

**Regression test.** Lives in the runner repository. Add unit tests for
`analyze_p2p_json()` and `analyze_comparison_delta()` with synthetic inputs
covering: same-freq identical panels (expect no warning), excess loss of
-0.05 dB (expect no warning), excess loss of -3.0 dB at pct_time=10 (expect
one warning, not two).

#### Test harness: mislabeled tests

Two test definitions have descriptions that contradict their parameters.
Cosmetic but trips up reviewers reading the summary.

1. `comprehensive-tests-v4.py:1187` — `p2p_pct_time10_loc10_sit10` is labeled
   "conservative reliability". By ITM convention higher percentile = signal
   exceeded that fraction of time = higher loss bound = more conservative;
   the actual numerics confirm (pct=10 → 122.7 dB ITM, pct=90 → 143.0 dB ITM).
   Swap "conservative" ↔ "optimistic" in this test and its `p2p_pct_time90`
   sibling at line 1196.

2. `comprehensive-tests-v4.py:1426-1433` — `cov_polar_h_manila` description
   says "horizontal polarization" but sets `polarization: 1`, which is
   Vertical per `constants.py:13`. Either change to `polarization: 0` to match
   the name, or rename to `cov_polar_v_manila`.

### Operational hardening — findings from 63-scenario revised harness (2026-05-26)

Robustness and developer-experience recommendations surfaced by the revised
test harness run.

#### Resolve simple vs advanced clutter duality for mode-independent params

BEL (building-type × frequency × elevation table lookup) and clutter percentiles
(modulate a statistical loss bound) are mode-independent. Forcing these into
"advanced only" adds no implementation benefit — it creates silent no-op paths
when users select the default clutter model.

**Proposed fix.**
1. Apply BEL uniformly in both simple and advanced clutter modes. BEL computation
   at `radio_coverage/tasks.py:148` already has access to all needed parameters.
2. Apply clutter percentile modulation in simple mode via the same lookup table
   indexing used in the simple-mode branches.
3. Keep advanced-specific SAALOS path separate.
4. Warn only when truly advanced-only params (e.g., SAALOS-specific constants)
   are set in simple mode.

This eliminates 5 of the 17 behavioral assertion failures in a single change.

### No compiled API reference documentation (LOW)

The project has excellent docstrings but no compiled API reference (Sphinx or
similar). The `docs/` directory is in `.gitignore`. Users and contributors
must read source files directly to understand the API.

**Proposed fix.** Add a `docs/` directory with a Sphinx `conf.py` and
auto-generate API references from docstrings. Wire into CI as a
`docs` job that fails on broken references. Low priority but improves
contributor onboarding.

**Status:** ⏳ Deferred — not included in v1.6.6.
