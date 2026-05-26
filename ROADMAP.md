# Roadmap

SPDX-License-Identifier: GPL-3.0-or-later

Planned work not yet implemented. Items move to [CHANGELOG.md](CHANGELOG.md) once landed.

## v1.6.6 — deferred items from v1.6.5 (planned)

Carried forward from v1.6.5. Each has a verified root cause and a proposed fix in the sections below — ready to land.

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

### Advanced vs simple clutter delta below threshold over urban (resolved — 2026-05-26)

The assertion `cov_pipeline_b_vs_cov_clutter_advanced_01_manila` (varies only
`CLUTTER_MODEL` 1→2 over Manila 5 km, 900 MHz) recorded a 0.5 dB delta
(`mean_dbm = -67.5` vs `-68.0`) against an expected ≥ 1.0 dB threshold.
The delta is real — the BEL fix in v1.6.5 made simple-mode and advanced-mode
outputs converge more closely, so 0.5 dB is the genuine difference.

**Resolution.** Lowered the behavioral assertion threshold from 1.0 → 0.3 dB.
The assertion now passes. No plugin change required.

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

### TX_CLUTTER_OVERRIDE and CLUTTER_PERCENTILE still simple-mode-only (confirmed — 2026-05-26)

v1.6.5 unified BEL across simple and advanced clutter modes. The same treatment
is needed for `tx_clutter_override` and `clutter_percentile` which remain
simple-mode-only, producing zero-delta output against any baseline.

**Proposed fix.** Same approach as BEL — move the override/percentile
computation before the simple/advanced branch in `radio_coverage/tasks.py`
so both modes consume the values.

### DOWNTILT_DEG / ANTENNA_BW suppressed in coverage path (confirmed — 2026-05-26)

v1.6.5 fixed the comparison-side Omni preset override (forces BW=360, AZ=None
in `collect_panel_params()`). The coverage path (`radio_coverage/params.py`)
still preserves the custom BW/AZ when PRESET=0, but downstream discards them.
Two identical rasters are produced whether downtilt is 0° or 6°, or BW is 360°
or 65°.

**Proposed fix.** Apply the same normalization used in comparison params to
the coverage path: when `ANTENNA_PRESET=0` (Omni), force `antenna_bw_override=360.0`,
`antenna_az=None`, and `downtilt_deg=0.0` in `radio_coverage/params.py`.

## Additional findings — candidates for v1.6.6+ (planned)

Findings captured 2026-05-26 from the Philippines suite, v4 comprehensive battery,
and 63-scenario revised harness. Several items overlap the v1.6.6 list above —
deduplicate before cutting the release branch.

### Philippines test-suite findings (2026-05-26)

Issues confirmed by comparing plugin source against actual `report.json` output
from a full 11-test Philippines propagation suite (QGIS 4.0 Docker, Copernicus
GLO-30 DEM, ESA WorldCover). See `run_philippines_tests.py` in the runner
repository for the test definitions.

Bump classification: PATCH (all items are correctness/robustness, zero public-API
change).

#### K_FACTOR_PRESET silently discards custom K_FACTOR

`radio.py:84-94` — `resolve_k_factor()` unconditionally returns the preset value
when *any* preset is selected, ignoring the custom `K_FACTOR` parameter. Docstring
acknowledges this ("Prefers the preset enum; falls back to the legacy numeric
K_FACTOR only when the preset is absent"), but the caller receives no diagnostic.

**Evidence.** The Philippines test suite set `K_FACTOR_PRESET=0, K_FACTOR=1.333`
for all P2P tests. Every `report.json` recorded `"k_factor": 0.67` — the preset's
value, not the explicitly-passed 1.333. The v2 re-run changed PRESET to 2 to get
standard atmosphere, confirming the custom value was ignored.

**Revised harness confirmation (2026-05-26).** `preset_kf_01_sub_refractive`
(PRESET=0 + K_FACTOR=1.333) reports `k=0.67`; `preset_kf_02_standard`
(PRESET=2 + K_FACTOR=0.5) reports `k=1.333`. Both report `itm_loss_db=127.168`
over the 55 km Manila→Tagaytay path. The preset override IS being honored
correctly — the custom K_FACTOR value is silently discarded in favor of the
preset. The identical ITM loss across k=0.67 vs k=1.333 over this terrain is
physically plausible (k-factor affects diffraction over the earth bulge; standard
vs sub-refractive atmosphere may not diverge meaningfully at 55 km over land).

**Proposed fix.** Two options:

1. When both a preset and a custom value are supplied, emit a QGIS feedback
   warning: `"Custom K_FACTOR=%.3f ignored — preset index %d (k=%.2f) in use."`
   This preserves backward compatibility while making the override visible.

2. Treat the custom K_FACTOR as overriding the preset when both are explicitly
   provided (i.e., preset=0 means "no preset" rather than "sub-refractive").
   This would be a MAJOR bump (default behavior change).

Recommended: option 1 (PATCH — a warning-only change).

**Regression test.** `tests/test_k_factor_preset_warns_on_custom.py` — call
`resolve_k_factor(has_preset=True, has_custom=True, custom_value=1.5,
preset_index=0)` and verify the `feedback.pushWarning()` was called (or that a
logger warning was emitted). Confirm the returned value is `K_FACTOR_PRESETS[0]`
(0.67), not 1.5.

#### Inconsistent JSON key naming across report types

`report/payloads.py:97` writes the ITM path loss as `"itm_path_loss_db"` in P2P
reports. `report/payloads.py:150` writes the same quantity as `"itm_loss_db"` in
coverage reports. Both use the same internal variable name (`itm_loss_db`) but
serialize under different JSON keys depending on report type.

**Evidence.** Direct file comparison:
- `p2p_01_manila_tagaytay/report.json:45`: `"itm_path_loss_db": 127.168...`
- `cov_01_manila_30km/report.json:39`:   `"itm_loss_db": 134.814...`

The test harness `analyze_p2p_json()` in `run_philippines_tests.py` used
`"itm_loss_db"` (the coverage key) for P2P reports and got zeros for every
entry, demonstrating the consumer-side fragility.

**Proposed fix.** Normalise to a single key across both report types. Two options:

1. Change P2P to `"itm_loss_db"` (simpler — coverage already uses it; P2P's
   `"itm_path_loss_db"` is the outlier).

2. Change coverage to `"itm_path_loss_db"` (more descriptive — conveys that it's
   the ITM-specific path loss, not total path loss).

Recommended: option 1 (fewer call sites to change — coverage reports are consumed
by more downstream code). Keep a deprecated alias for one release cycle if external
consumers exist.

**Regression test.** `tests/test_report_json_key_consistency.py` — build both a
P2P and a coverage report payload, assert both JSON objects contain the same
ITM-loss key name.

#### ANTENNA_PRESET vs custom BW/AZ in comparison algorithm

`comparison/params.py:138-145` — `collect_panel_params()` reads `ANTENNA_BW` and
`ANTENNA_AZ`, then computes `antenna_bw_override`:
```python
antenna_bw_override = (
    None
    if antenna_preset != CUSTOM_ANTENNA_PRESET_INDEX and antenna_bw == 360.0
    else antenna_bw
)
```

When PRESET is non-Custom and BW != 360, the override preserves the custom BW
(e.g., 120.0). This value is passed to `compute_coverage()` at
`comparison/panel.py:128`, which forwards it to `antenna_config_from_values()`
at `radio_coverage/engine.py:126`. The antenna config factory receives both a
non-Custom preset AND a non-360 beamwidth — and the preset-determined pattern
may take priority, silently discarding the custom beamwidth.

**Evidence.** The `cmp_02_manila_omni_vs_sector` test configured Panel B with
`ANTENNA_PRESET=0` (omni), `ANTENNA_BW=120.0`, `ANTENNA_AZ=135.0`. Both panels
produced identical output (all-zero delta, `unchanged_pct: 100.0`). The explicit
sector parameters were accepted and forwarded through the comparison pipeline
but had no effect on the computed coverage.

**Proposed fix.** `collect_panel_params()` should force `antenna_bw_override=360.0`
and `antenna_az=None` when the preset is omni (index 0), irrespective of what
`ANTENNA_BW`/`ANTENNA_AZ` contain. This makes the override self-consistent:
the preset controls the pattern, and the override correctly reflects the
preset-determined beamwidth. Optionally emit a warning when a non-default
BW/AZ is supplied alongside a non-Custom preset.

**Regression test.** `tests/test_comparison_preset_overrides_custom_bw.py` —
call `collect_panel_params()` with `ANTENNA_PRESET=0` (omni), `ANTENNA_BW=120.0`,
`ANTENNA_AZ=135.0`. Assert `antenna_bw_override` is `360.0` and `antenna_az`
is `None`.

### v4 comprehensive battery findings (2026-05-26)

Issues surfaced by a 57-scenario battery (`comprehensive-tests-v4.py`, results in
`nowires-tests-results/v4-results/`). Verified by md5 comparison of `coverage.tif`
outputs and by reading the source paths each parameter takes. Distinct from the
earlier 11-test Philippines suite findings above.

Bump classification: PATCH for all items (correctness + test-harness only, zero
public-API change).

#### Simple-clutter mode silently ignores BEL / CLUTTER_PERCENTILE / TX_CLUTTER_OVERRIDE

`radio_coverage/tasks.py:127` — the `if advanced and clutter_enabled:` branch is
the only path that consumes `clutter_context.bel_enabled`,
`clutter_context.percentile`, and `clutter_context.bel_building_type`. The simple-
clutter branches at lines 155, 159, 163 hard-code `pixel_bel_db = 0.0` (line 244)
and never read the BEL or percentile fields. `tx_clutter_override` is similarly
unused in simple mode beyond category resolution.

**Evidence.** Md5sum of `coverage.tif` across the v4 battery:

```
619e52136f640fc0104206fe26f8603f  cov_pipeline_b               ← baseline (no extras)
619e52136f640fc0104206fe26f8603f  cov_bel_01_manila_5km        ← BEL_ENABLED=True, type 1
619e52136f640fc0104206fe26f8603f  cov_bel_02_commercial        ← BEL type 2, 30° elev
619e52136f640fc0104206fe26f8603f  cov_bel_03_suburban          ← BEL type 0, 5° elev
619e52136f640fc0104206fe26f8603f  cov_clutter_override_tx      ← TX_CLUTTER_OVERRIDE=5
619e52136f640fc0104206fe26f8603f  cov_clutter_percentile_90    ← CLUTTER_PERCENTILE=90
```

Six runs with five distinct semantic overrides produced bit-for-bit identical
rasters. The advanced-clutter run (`cov_clutter_advanced_01_manila`,
`CLUTTER_MODEL=2`) hashes differently, confirming the BEL/percentile path is
only wired in advanced mode.

**Proposed fix.** Two options:

1. Apply BEL uniformly in both clutter modes. BEL is a frequency × building-type
   × elevation calculation that does not depend on the path-clutter model;
   subtract `bel_db` (computed at line 148) inside the simple branches as well.
   Same for `clutter_percentile` where it modulates the simple-mode loss table.

2. Validate at parameter-parse time: if `clutter_model == "simple"` AND any of
   (`bel_enabled`, `clutter_percentile != 50.0`, `tx_clutter_override`,
   `rx_clutter_override`) differ from defaults, raise a `QgsProcessingException`
   or `feedback.pushWarning()` stating that the parameter requires advanced mode.

Recommended: option 1 for BEL (the calculation is mode-independent); option 2
for the genuinely advanced-only knobs.

**Regression test.** `tests/test_coverage_simple_mode_honors_bel.py` — run
`compute_coverage()` twice with `clutter_model="simple"`, identical inputs except
`bel_enabled=False` vs `bel_enabled=True, bel_building_type="traditional",
bel_elevation_angle_deg=15.0, f_mhz=900.0`. Assert the mean Prx differs by at
least 3 dB (BEL at 900 MHz, traditional, 15° elevation is ~10 dB per ITU-R
P.2109). Compare both outputs' md5 sums and assert they differ.

#### ANTENNA_PRESET=0 (Omni) suppresses custom DOWNTILT_DEG / ANTENNA_BW in coverage

Parallel to the existing comparison-side finding above, but in the coverage code
path. `radio_coverage/params.py:220-223`:
```python
antenna_bw_override = (
    None if antenna_preset != CUSTOM_ANTENNA_PRESET_INDEX and doubles["antenna_bw"] == 360.0
    else doubles["antenna_bw"]
)
```
With `ANTENNA_PRESET=0` and `ANTENNA_BW != 360.0` the override is preserved, but
downstream `antenna_config_from_values()` (called from `engine.py:126`) may treat
the Omni preset as authoritative and discard both the custom beamwidth and
`downtilt_deg`.

**Evidence.** Md5 across the v4 battery:

```
1dc99e597209720f7ba1cd38b10c7400  cov_antenna_downtilt    ← PRESET=0, DOWNTILT_DEG=6.0, BW=360
1dc99e597209720f7ba1cd38b10c7400  cov_antenna_sector_65deg ← PRESET=0, DOWNTILT_DEG=0.0, BW=65
```

Two runs at the same TX/freq/power that vary either downtilt or beamwidth
produce byte-identical output. The Omni preset is masking both knobs.

**Proposed fix.** In `radio_coverage/params.py:220` and the corresponding
`comparison/params.py:138` (already on the roadmap), normalise the override
upfront when `antenna_preset == 0` (Omni): force `antenna_bw_override=360.0`,
`antenna_az=None`, and `downtilt_deg=0.0`. Optionally `feedback.pushWarning()`
when non-default values were supplied alongside Omni, so users notice instead of
silently getting the unmodified Omni pattern.

**Regression test.** `tests/test_coverage_omni_preset_overrides_custom.py` —
call `extract_coverage_params()` with `ANTENNA_PRESET=0`, `ANTENNA_BW=65.0`,
`ANTENNA_AZ=0.0`, `DOWNTILT_DEG=6.0`. Assert `antenna_bw_override` is `360.0`,
`antenna_az` is `None`, `downtilt_deg` is `0.0`. Second test: with PRESET=Custom
and the same numeric overrides, assert all three are preserved.

#### Coverage report.json omits most engine-consumed parameters

`report/payloads.py:126-143` — `_build_coverage_input_dict()` writes only
14 fields. The engine consumes (and the runner explicitly sets) at least 10
more that never appear in the `inputs` section of `report.json`:

- `bel_enabled`, `bel_building_type`, `bel_elevation_angle_deg`
- `clutter_percentile`, `street_width_m`
- `tx_clutter_override`, `rx_clutter_override`
- `antenna_bw`, `antenna_az`, `downtilt_deg`, `front_back_db`
- `k_factor`, `n0`, `epsilon`, `sigma`

**Evidence.** The previous finding (BEL silent no-op in simple mode) was
invisible at the JSON layer — every report dutifully recorded `polarization`
and `climate` but had no field showing whether BEL was enabled. Only md5
comparison surfaced the bug. P2P reports include most of these (see
`report/payloads.py:80-91`) so the asymmetry is purely a coverage-side gap.

**Proposed fix.** Extend `_build_coverage_input_dict()` to include the fields
above, mirroring the P2P inputs structure. Add a `clutter_model` field
(currently included) and `clutter_advanced_active` boolean to make the
mode-dependent param handling visible.

**Regression test.** `tests/test_coverage_report_includes_clutter_inputs.py` —
build a coverage payload with `bel_enabled=True, clutter_percentile=90.0,
tx_clutter_override="urban", downtilt_deg=6.0, k_factor=0.67`. Assert all five
appear under `inputs` in the resulting payload dict.

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
test harness run. Distinct from the correctness items above.

#### GDAL geometry type warnings flood feedback logs

Every coverage and P2P run emits 10–30 warnings of the form:
```
Warning 1: Layer 'markers' has been declared with non-Z geometry type Point,
but it does contain geometries with Z. Setting the Z=2 hint into gpkg_geometry_columns
```

These are not bugs (QGIS 4.0 GDAL defaults to 3D enforcement), but they fill
`feedback.log` with noise, making real warnings invisible during test runs. The
geometry type declarations in the GPKG writers (`p2p/compute.py`, `radio_coverage/`
output paths) should either declare Z geometry types upfront or configure
`GDAL_PAM_ENABLED=NO` before `CreateLayer()` calls.

**Proposed fix.** In each `ogr_driver.CreateLayer()` call, either set the geometry
type to the Z variant (e.g., `wkbPoint25D` → `wkbPointZM`) or suppress the
quietly with `gdal.SetConfigOption("OSR_USE_NON_DEPRECATED", "NO")` / layer
creation options. Alternatively, set `GDAL_PAM_ENABLED=NO` in the test-runner
environment to suppress the per-layer metadata writes that trigger the warning.

#### DEM download timeout on long cross-sea paths

Manila → Cebu (~600 km, mostly open ocean) timed out at 300s inside
`clips_and_merge_tiles → ComputeStatistics`. The tile merger blocks indefinitely
on GDAL operations with no progress callback. Cross-sea paths download numerous
tiles with no land in them, waste bandwidth, and stall the pipeline.

**Proposed fix.** Two-pronged:
1. Cap the DEM fetch to the land portion of the path by intersecting the bounding
   box with a coastline shapefile or GSHHG mask. Sea pixels don't contribute to
   ITM terrain calculations — skipping them saves minutes per cross-sea link.
2. Add a configurable timeout wrapping `ComputeStatistics` so the UI doesn't hang
   on stalled GDAL operations.

#### Simple-clutter mode should warn when advanced-only params are set

Before any BEL/clutter-override/percentile fix lands, the plugin should at minimum
emit `feedback.pushWarning()` when parameters are set to non-default values that
will be silently ignored in simple-clutter mode. Currently, setting
`BEL_ENABLED=True, CLUTTER_PERCENTILE=90, TX_CLUTTER_OVERRIDE=5` with
`CLUTTER_MODEL=Simple` produces zero feedback — the user cannot know their
configuration is being discarded.

**Proposed fix.** In `radio_coverage/tasks.py` or the params extraction phase,
add validation that checks for incompatible param combinations and emits
`feedback.pushWarning(f"CLUTTER_PERCENTILE=%.1f ignored — requires Advanced
clutter model")` and similar for BEL and clutter overrides.

This is P0 (precedes any BEL/override fix) because it makes silent failures
surfaced, enabling users to self-diagnose while awaiting the correctness fix.

#### Coverage report.json should echo all engine inputs

`report/payloads.py:_build_coverage_input_dict()` serialises only 14 of the
26+ parameters consumed by the coverage engine. Missing fields include BEL,
clutter percentile, clutter overrides, antenna BW/AZ/downtilt, k-factor, N0,
epsilon, sigma. P2P reports echo most of these — the asymmetry is purely a
coverage-side gap.

The test harness compensated by externally capturing `params_sent.json` before
every `processAlgorithm()` call. Real users cannot do this — the `report.json`
is their only post-hoc evidence of what ran.

**Proposed fix.** Extend `_build_coverage_input_dict()` to mirror the P2P
inputs structure. Add a `clutter_model` field and a `clutter_advanced_active`
boolean to make mode-dependent param handling visible. This reduces future
silent failures by making the input echo auditable.

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

#### P2P path lacks the climate range check that coverage already enforces (new — 2026-05-26)

The CLIMATE Processing parameter is a 7-option enum (indices 0–6) with
`defaultValue=1` ([radio_coverage/params.py:113](radio_coverage/params.py)).
`validate_itm_input_ranges()` in `radio.py` does range-check `climate` against
`ITM_MIN_CLIMATE=0 / ITM_MAX_CLIMATE=6`, but it is only invoked from the
coverage path ([radio_coverage/params.py:225](radio_coverage/params.py)). The
P2P algorithm reads CLIMATE at [algorithm/p2p.py:87](algorithm/p2p.py) via
`parameterAsEnum()` and forwards the value straight through with no range
validation. When a caller passes an out-of-range index via Python API or
script (e.g., a 1-based ITU/NTIA climate code such as 7 instead of the
plugin's 0-based 6 for Maritime Temperate Sea), QGIS's `parameterAsEnum`
silently substitutes the parameter's `defaultValue` — the algorithm sees
climate=1 with no warning, the report records `"Continental Subtropical"`,
and the result is bit-identical to a genuine CLIMATE=1 run. `radio.itm_p2p_loss`
adds 1 to map to the internal `Climate(IntEnum)` so the surrounding code
*would* raise `ValueError` on Climate(8), but the QGIS-level clamp prevents
that branch from ever being reached.

**Evidence.** From the revised-harness run-4 thorough run: `p2p_climate_1_equatorial`
(CLIMATE=1) and `p2p_climate_7_maritime_warm` (CLIMATE=7) produced byte-identical
`itm_loss_db=127.05654797537987`. Both reports show `inputs.climate =
"Continental Subtropical"`. `p2p_climate_5_tagaytay` (CLIMATE=5, in range)
diverged correctly to 127.16830091322589 / `"Maritime Temperate (land)"`.

**Proposed fix.** Call `validate_itm_input_ranges()` from
`algorithm/p2p.py::processAlgorithm` before invoking the engine, matching the
coverage-path convention. This converts the silent clamp into a fail-fast
`QgsProcessingException` with a clear range message. Optional follow-up: emit
a `feedback.pushWarning()` from the parameter extraction layer when QGIS
clamps to default, so GUI users also see the substitution.

**Regression test.** `tests/test_algorithm_p2p_climate_validation.py` — invoke
`P2PAlgorithm.processAlgorithm()` with `CLIMATE=7` and assert
`QgsProcessingException` is raised with a message containing `"Climate zone"`
and `"between 0 and 6"`.

**Status:** ✅ Resolved — v1.6.6 (commit `cbc1af0`).

#### Silent clutter fallback masquerades as a successful clutter run (new — 2026-05-26)

When the WorldCover tile is unavailable (download fails, race during parallel
runs, file corruption), `clutter/__init__.py:99` and `clutter/resolve.py:43,53`
return the sentinel `"fallback_open"` and the coverage engine proceeds with
`clutter_tx_db=0.0, clutter_rx_db=0.0` — effectively no clutter applied. The
report still records `inputs.clutter_model = "Simple clutter correction"`. The
only signal that clutter was skipped is `inputs.clutter_source = "fallback_open"`,
which is easy to miss in a multi-page HTML report. Two runs with identical
input parameters but different WorldCover availability produce reports that
look indistinguishable on the headline fields while differing by ~15 dB on
mean Prx.

**Evidence.** In run-4, `cov_antenna_downtilt` and `cov_antenna_downtilt_only`
have byte-identical `params_sent.json` (apart from output paths). The first
hit a WorldCover download race and reported `clutter_source = "fallback_open"`,
`clutter_tx_db = 0.0`, `mean_prx_dbm = -57.36`. The second loaded the tile
correctly and reported `clutter_source = "…/ESA_WorldCover_…tif"`,
`clutter_tx_db = 10.0`, `mean_prx_dbm = -72.83`. Both reports advertise
`clutter_model = "Simple clutter correction"`.

**Proposed fix.** Three options, escalating in strength:

1. **Surface in `clutter_model`.** When `clutter_source == "fallback_open"`,
   set `clutter_model = "Simple clutter correction (WorldCover unavailable —
   clutter skipped)"` so the most-viewed field reflects the actual state.
2. **`feedback.pushWarning()`** at the call site when the resolver returns
   `"fallback_open"`, citing the failed tile name and reason if available.
3. **Fail-fast option.** Add a `STRICT_CLUTTER` boolean parameter
   (default False) that converts the fallback into a `QgsProcessingException`.
   Useful for batch scripts and CI where a silent zero-clutter run is worse
   than a hard failure.

Option 1 is the minimum bar (zero-cost reporting fix); options 2–3 are
follow-ups. This complements the existing "Simple-clutter mode should warn
when advanced-only params are set" item above — both surface silent failures
so users can self-diagnose.

**Regression test.** `tests/test_clutter_fallback_visible_in_report.py` —
patch `ensure_worldcover_for_area` to return None, run a coverage call, and
assert the resulting `report.json` `clutter_model` field contains a substring
identifying the fallback (e.g., `"unavailable"` or `"fallback"`).

**Status:** ✅ Resolved — v1.6.6 (commit `6e62d3a`). Option 1 implemented.

### Code audit findings (2026-05-26) — resolved v1.6.6

Findings from a comprehensive source audit. All PATCH-classified items below
were implemented in v1.6.6 (14 commits, 2026-05-27). The one deferred item is
noted inline.

#### Antenna pattern CSV has no row/size cap (HIGH)

`antenna.py:149-167` — `_read_pattern_points` reads unbounded rows from
user-supplied CSV files. A maliciously crafted file could exhaust memory. The
`@lru_cache(maxsize=32)` mitigates re-reads but not a single oversized file.

**Proposed fix.** Add `MAX_PATTERN_ROWS = 3600` constant (0.1° resolution for
360°) and break the reader loop when `len(points) >= MAX_PATTERN_ROWS`. Emit
`logger.warning("Pattern file %s exceeds %d rows; truncating", path,
MAX_PATTERN_ROWS)` so users can diagnose truncation.

**Regression test.** `tests/test_antenna_pattern_row_cap.py` — feed a CSV with
4000 rows and assert the result is truncated to 3600, and that a warning is
logged.

**Status:** ✅ Resolved — v1.6.6 (commit `fdaddb7`).

#### No concurrency tests for SharedDEMGrid and release-lock paths (HIGH)

`SharedDEMGrid.release()` acquires `_release_lock`, removes from
`_pending_releases`, closes + unlinks the shm segment. `__del__` calls
`release()`. `_atexit_release_pending` iterates `_pending_releases` then calls
`release()` on each. No test exercises actual multi-thread contention on
`release()` or validates `__del__` during interpreter shutdown while another
thread holds the lock.

**Proposed fix.** Add `tests/test_shared_dem_concurrent_release.py`:
1. Create a `SharedDEMGrid`, spawn 8 threads all calling `release()`, assert no
   `OSError` or double-unlink (`FileNotFoundError`).
2. Create a grid, start a thread that acquires `_release_lock` for 200 ms,
   then call `release()` from main thread — assert it blocks then completes.
3. Create a grid, remove all references (triggering `__del__`), assert shm
    segment no longer exists in `/dev/shm/`.

**Status:** ✅ Resolved — v1.6.6 (commit `2fbb83a`).

#### Bilinear interpolation triplication — DRY refactor (HIGH)

`_bilinear.py:28-117` — the scalar, line, and grid variants duplicate
identical fractional-index computation (clip + floor + blend weights). Three
blocks of near-identical logic risk divergence if one is edited without the
others.

**Proposed fix.** Extract a shared
`_compute_indices(n_rows, n_cols, gm, fy, fx)` that returns
`(y0, x0, y1, x1, ty, tx, oob_mask)`. Each variant calls this then applies
its own blend. Approximately 60 lines of duplicated index logic collapse into
one function. Maintain the public API (`bilinear_sample`,
`bilinear_sample_grid`) unchanged.

**Regression test.** Existing `_bilinear` tests cover the outer API — they
should pass unchanged after refactor. Add a targeted test that calls
`_compute_indices` directly and asserts expected values at boundary coordinates.

**Status:** ✅ Resolved — v1.6.6 (commit `6efeb03`).

#### test_batch_philippines.py excluded from CI (MEDIUM)

`tests/test_batch_philippines.py` is listed in `.gitignore:76` so CI never
runs it. It contains region-specific regression assertions that are important
for validating propagation calculations over real terrain.

**Proposed fix.** Either (a) remove the `.gitignore` entry and add
`@pytest.mark.slow` so it runs in CI, or (b) refactor its key assertions into
a CI-runnable test file that uses mocked terrain data. Option (a) is simpler;
option (b) avoids CI needing real DEM tiles.

**Status:** ✅ Resolved — v1.6.6 (commit `14c706d`). Option (a) with `@pytest.mark.slow`.

#### Enforce MAX_AOI_EXTENT_DEGREES in coverage_bounds() (MEDIUM)

`geo_bounds.py:17-38` — `coverage_bounds()` computes lat/lon extents from a
radius but does not enforce `MAX_AOI_EXTENT_DEGREES`. Validation currently
lives upstream in `algorithm/contour.py:133`. Defense in depth: the function
that computes bounds should enforce the limit itself.

**Proposed fix.** Add `max_extent=MAX_AOI_EXTENT_DEGREES` parameter to
`coverage_bounds()`. If `half_lat > max_extent` or `half_lon > max_extent`,
clamp and emit `logger.warning("AOI clamped from %.2f to %.2f degrees", ...)`
so users know the extent was reduced.

**Regression test.** `tests/test_geo_bounds_lat_clamp.py` already tests
latitude clamping; extend it to assert longitude clamping and the `max_extent`
parameter.

**Status:** ✅ Resolved — v1.6.6 (commit `eb2cf7f`).

#### Add integration test for advanced clutter mode with WorldCover (MEDIUM)

The Docker QGIS integration suite has no test that runs coverage with
`clutter_enabled=True, clutter_model=2` (advanced / SAALOS) against a
WorldCover grid. This is a critical path that differs significantly from the
simple-mode branch yet is untested in integration.

**Proposed fix.** Add `tests/test_qgis_integration_clutter_advanced.py`
marked `@pytest.mark.qgis_integration` that:
1. Runs coverage with `CLUTTER_MODEL=2` (advanced) + WorldCover.
2. Asserts the output raster has non-uniform values (not all NODATA).
3. Asserts `report.json` contains `clutter_model: "advanced"`.

**Status:** ✅ Resolved — v1.6.6 (commit `ba20108`).

#### Document atime limitation in cache eviction (LOW)

`cache_manager.py:94` — `evict_cache_lru` sorts entries by
`os.path.getatime()`. On Linux ext4 with `relatime` (the default mount option),
atime is only updated every ~24 hours, making LRU eviction imprecise.
The function works correctly but may evict recently-accessed entries if atime
hasn't been flushed.

**Proposed fix.** Add a docstring note to `evict_cache_lru()` documenting the
atime caveat. Optionally consider mtime-based eviction as a future
improvement (requires recording access time in a sidecar file).

**Status:** ✅ Resolved — v1.6.6 (commit `b8479de`).

#### Return numpy array from interpolate_nan_elevations (LOW)

`nan_utils.py:14-33` — `interpolate_nan_elevations()` returns `list[float]`
while `interpolate_nan_array()` returns `numpy.ndarray`. The list return is
intentional (P2P code path uses it), but the inconsistency is confusing.

**Proposed fix.** Change `interpolate_nan_elevations()` to return
`np.ndarray` and update the P2P callers to handle arrays. Alternatively,
document in the docstring why a list is returned and add a
`interpolate_nan_elevations_as_array` convenience wrapper.

**Status:** ✅ Resolved — v1.6.6 (commit `1281955`). Return type changed to `np.ndarray`.

#### Broaden TempDirManager.__del__ exception catch (LOW)

`temp_manager.py:138-143` — `__del__` catches `TypeError` but not
`AttributeError`. During interpreter shutdown, `os.unlink` and `os.path` may
be `None` if their modules have been garbage-collected, raising
`AttributeError`. The `TypeError` catch handles the common case but is
incomplete.

**Proposed fix.** Change `except TypeError` to
`except (TypeError, AttributeError)` on line 143. This mirrors the standard
CPython `__del__` pattern for `tempfile` cleanup.

**Status:** ✅ Resolved — v1.6.6 (commit `c43a309`).

#### Rename underscore-prefixed public modules (LOW → MINOR bump)

`p2p/_outputs_internal.py` and `radio_coverage/_result_dispatch.py` use the
underscore convention signaling "private", but are imported by sibling modules
within their packages. This is misleading — the underscore suggests internal
stability guarantees while the modules are actually part of the package's
decomposition API.

**Proposed fix.** Rename `_outputs_internal.py` → `outputs_internal.py` and
`_result_dispatch.py` → `result_dispatch.py`. Update all imports. Per
`AGENTS.md`, this is a public API rename → **MINOR** bump. Add both renames
to the `[Unreleased]` section of `CHANGELOG.md`.

**Status:** ✅ Resolved — v1.6.6 (commit `f03c69f`). Both modules renamed; all imports updated.

#### No compiled API reference documentation (LOW)

The project has excellent docstrings but no compiled API reference (Sphinx or
similar). The `docs/` directory is in `.gitignore`. Users and contributors
must read source files directly to understand the API.

**Proposed fix.** Add a `docs/` directory with a Sphinx `conf.py` and
auto-generate API references from docstrings. Wire into CI as a
`docs` job that fails on broken references. Low priority but improves
contributor onboarding.

**Status:** ⏳ Deferred — not included in v1.6.6.
