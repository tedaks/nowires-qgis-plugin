# Roadmap

SPDX-License-Identifier: GPL-3.0-or-later

Planned work not yet implemented. Items move to [CHANGELOG.md](CHANGELOG.md) once landed.

## v1.6.3 — released 2026-05-24

All planned items landed. See [CHANGELOG.md](CHANGELOG.md#163---2026-05-24) for details.

## v1.6.4 — coverage push ✅

Target: 85% combined unit + integration test coverage.
**Achieved: 85%** (unit + GDAL + QGIS integration via Docker QGIS 4.0 + matplotlib).

Key improvements:
- `algorithm/coverage_comparison.py`: 26% → 91%
- `algorithm/p2p.py`: 33% → 99%
- `comparison/outputs.py`: 25% → 95%
- `radio_coverage/legend.py`: 24% → 74%
- `contour/smoothing.py`: 75% → 86%
- `p2p/compute.py`: 95% → 97%

- ~~Increase `fail_under` coverage threshold~~ ✅ 59% → 65%
- ~~106 unit tests for core modules~~ ✅ done
- ~~12 non-Qt GUI helper tests~~ ✅ done
- ~~21 Docker QGIS + algorithm execution tests~~ ✅ done
- ~~7 comparison outputs + 4 contour module tests~~ ✅ done
- ~~12 Qt widget tests with matplotlib~~ ✅ done
- Remaining uncovered (~990 lines): Qt GUI lifecycle (nowires.py, p2p/chart.py, three_d.py), GDAL pipelines (contour.py, pipeline.py) — these require either QMainWindow infrastructure or real Copernicus DEM downloads

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

## v1.6.5 — review-driven hardening ✅

Findings from a manual code review (2026-05-24). Each item below was verified by reading
the source — speculative findings from the same review pass are not listed.

Bump classification: PATCH (correctness + robustness, zero public-API change). Each
item lands with a regression test that fails without the patch, per TDD convention
since v1.5.0.

**Re-verified 2026-05-26 against HEAD `79946e1`.** All source-level claims still
hold: SAALOS clamp asymmetry, redirect scheme gap, missing jitter, broad `except`
in shm finalizer, sanitiser whitespace gap, ITM JSON key inconsistency, simple-
clutter BEL no-op (md5-confirmed across 6 v4 runs), ANTENNA_PRESET=Omni override
(md5-confirmed across 2 v4 runs), and the coverage-report input-echo gap. The
*Retry backoff lacks jitter* call-site list was corrected to reflect the
indirect `wait_secs` path. The previous *Test harness P2P JSON key mismatch*
item was dropped — the harness it referenced no longer exists, and the current
runner already reads the correct key; the plugin-side root cause is tracked
below under *Inconsistent JSON key naming across report types*.

### SAALOS scalar / vector numerical asymmetry

The vectorised SAALOS path in `clutter/_saalos_vec.py` defensively clamps three
quantities that the scalar path in `clutter/saalos.py` does not. At edge inputs the
two implementations diverge — scalar returns ±inf or NaN where vector returns a
finite loss. Coverage maps (which always use the vector path) and P2P analyses
(which use the scalar path for single-link compute) will therefore disagree on
the same input.

| Site | Scalar (unsafe) | Vector (safe) |
|---|---|---|
| `saalos.py:79` | `crpc = dp - 1.0 / dp` | `_saalos_vec.py:44` clamps `dp` to ≥ 1.0 in the denominator |
| `saalos.py:109` | `math.log10(tsp)` | `_saalos_vec.py:80` clamps `tsp` to ≥ 1e-30 |
| `saalos.py:118` | `math.log10(rsp)` | `_saalos_vec.py:94` clamps `rsp` to ≥ 1e-30 |

**Trigger inputs.** After the 5-iteration refraction loop, `dp` shrinks toward zero
at grazing incidence (line 82: `dp = pd - d1a`). `tsp = 1 - rsp` reaches zero when
the reflection coefficient `q → ±1` (lines 92–104). `rsp = q²` reaches zero when
`q → 0`, i.e. when `cttc ≈ ctic` at the matched-angle case.

**Proposed fix.** Mirror the vector clamps into the scalar path so both
implementations are bit-for-bit equivalent on the safe range and finite on the
edge range:

```python
# saalos.py:79
crpc = dp - 1.0 / max(dp, 1.0)

# saalos.py:109
arte = 0.0195 * crpc - 20.0 * math.log10(max(tsp, 1e-30))

# saalos.py:118
arte = d1a * q - (18.0 * math.log10(max(rsp, 1e-30))) / math.exp(hone / 37.5)
```

**Regression test.** `tests/test_saalos_scalar_vector_parity.py` —
property-based test (hypothesis) drawing `(d_m, cch_m, h_tx_m, h_rx_m,
h_rx_gnd_m, pol, f_mhz)` from the documented input domain plus boundary cases
(`dp → 0`, `q → ±1`, `q → 0`). For each input, assert
`clutter_loss_saalos(...) == clutter_loss_saalos_vec(...)` within 1e-9, and assert
both are finite. Currently fails on the boundary draws.

### Tile download redirect scheme check

`tile_download_base.py:101` compares only `urlsplit(final_url).netloc` against
`base_url`, not the scheme. A redirect from `https://copernicus-dem-30m.s3...` to
`http://copernicus-dem-30m.s3...` passes the check and downloads the tile over
plaintext. With a hostile network operator (or a poisoned resolver) this enables
a downgrade attack: the cert pinning is effectively skipped on the second hop.

**Proposed fix.**

```python
if base_url is not None:
    base = urlsplit(base_url)
    final = urlsplit(final_url)
    if (final.netloc.lower() != base.netloc.lower()
            or final.scheme != base.scheme):
        raise RuntimeError("Unexpected redirect to: " + final_url)
```

**Regression test.** `tests/test_tile_download_redirect_scheme.py` — install a
mock opener that 302-redirects `https://host/x.tif` to `http://host/x.tif` and
assert `download_tile_with_retry(...)` returns `None` (or raises) without reading
the body.

### Retry backoff lacks jitter

`tile_download_base.py:140, 153, 198` sleep `2 ** attempt` directly; the
retryable-HTTP branch computes `wait_secs = 2 ** attempt` at lines 175 / 177
and consumes it via `time.sleep(wait_secs)` at line 184. All four call sites
lack jitter. When multiple QGIS workers (`NOWIRES_MAX_WORKERS` defaults up to
16) each retry the same tile after a 503 or transient timeout, they retry in
lockstep — the second wave is more likely to provoke the same throttling, then
the third wave, etc. (thundering herd).

**Proposed fix.** Move backoff to a helper:

```python
# tile_download_base.py (module scope)
import random

def _backoff_seconds(attempt: int) -> float:
    return 2 ** attempt + random.uniform(0, 1)
```

…and replace every `time.sleep(2 ** attempt)` and `wait_secs = 2 ** attempt`
with `_backoff_seconds(attempt)`. The `Retry-After` branch keeps its
header-supplied value unchanged.

**Regression test.** `tests/test_tile_download_backoff_jitter.py` — seed
`random` deterministically, call `_backoff_seconds(attempt)` for attempts 0–3,
assert each result is in `[2**attempt, 2**attempt + 1)` and that two
consecutive calls with different seeds differ.

### URL logged unsanitised to QGIS feedback

`tile_download_base.py:83` calls `feedback.pushInfo("Downloading: " + tile_url)`.
Today's `tile_url` is built from a hard-coded base + tile name + extension, so
no query string can be appended — but the base URL is a constructor argument
and a future caller passing a presigned S3 URL would leak the signature into
the QGIS message log.

**Proposed fix.** Strip the query string for the user-facing log; keep the full
URL in the structured `logger.debug` call.

```python
from urllib.parse import urlsplit, urlunsplit

def _redact_query(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(parts._replace(query="", fragment=""))

if feedback:
    feedback.pushInfo("Downloading: " + _redact_query(tile_url))
logger.debug("Downloading full URL: %s", tile_url)
```

**Regression test.** `tests/test_tile_download_url_redaction.py` — pass a URL
with a `?X-Amz-Signature=...` query, capture pushInfo, assert the signature is
not in the captured string.

### Silent exception suppression in shared-memory finalizer

`radio_coverage/pool.py:129-130, 143-144` swallow every exception from
`SharedMemory.close()` / `.unlink()` with `except Exception: pass`. Real
failures (permission errors, double-unlink, missing segment) are invisible.
Past `/dev/shm` cleanup bugs (`test_cleanup_stale_shm_scoping`) were exactly
this class.

**Proposed fix.**

```python
def _final_cov_pool():
    with _cov_lock:
        global _cov_shm, _cov_grid_data
        if _cov_grid_data is not None:
            _cov_grid_data = None
        if _cov_shm is not None:
            try:
                _cov_shm.close()
                _cov_shm.unlink()
            except FileNotFoundError:
                pass  # already unlinked — normal on second run
            except OSError as exc:
                logger.debug("shm finalizer: %s", exc)
            _cov_shm = None
```

Apply the same narrowing to the close-only branch at line 142.

**Regression test.** `tests/test_pool_finalizer_logs_errors.py` — monkeypatch
`SharedMemory.unlink` to raise `PermissionError`, call `_final_cov_pool()` under
`caplog`, assert the message is logged at DEBUG and that the function does not
raise.

### Sanitiser whitespace coverage

`sanitizers.py:6` defines `_UNICODE_WHITESPACE = "\t\r　  ﻿"`
— ASCII space ` ` is intentionally **not** in the set, so `" =cmd"` with a
leading regular space bypasses the formula-injection guard. Excel auto-trims
leading whitespace when rendering cells, so this is exploitable against an
Excel consumer of the CSV.

**Decision required.** Two options:
1. Add `" "` to `_UNICODE_WHITESPACE`. Risk: trims legitimate leading spaces in
   user-supplied free-text fields (point notes, custom IDs). Existing
   `test_batch_writer_csv_injection.py` does not cover this case.
2. Keep stripping conservative and instead match the formula-trigger check
   against the **first non-whitespace character** rather than `s[0]`. Preserves
   the original string verbatim while still catching `" =cmd"`.

Preferred: option 2 (preserves user content). Implementation sketch:

```python
def csv_safe(value):
    s = str(value).replace("\r", " ").replace("\n", " ")
    stripped = s.lstrip(_UNICODE_WHITESPACE + " ")
    if stripped and stripped[0] in _FORMULA_TRIGGER_CHARS:
        return "'" + s
    if stripped.startswith("-") and len(stripped) > 1:
        try:
            float(stripped)
        except ValueError:
            return "'" + s
    return s
```

**Regression test.** Extend `test_batch_writer_csv_injection.py` with
`(" =SUM(A1)", "'  =SUM(A1)")` and similar cases for `+`, `@`, U+2212.

### Release shape

Group by category per `AGENTS.md`:
- Security: redirect scheme check, URL redaction, sanitiser whitespace
- Correctness: SAALOS scalar/vector parity
- Robustness: backoff jitter, shm finalizer logging

One PR per category. Manual QGIS UI test not required (no Qt-widget changes).

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

### Revised test harness — behavioral assertion confirmation (2026-05-26)

The revised test harness (`revised-tests/`, 48 files, ~2,750 LOC) ran 63 scenario
tests + 17 behavioral assertions against the current plugin in QGIS 4.0 Docker.
Results: 52/63 scenarios passed, 17 behavioral assertions produced 13 failures
(4 `xfail` — expected failures for known plugin bugs). Run saved at
`nowires-tests-results/revtest-run-1/`.

**Key findings that confirm roadmap entries below:**

- **BEL silently no-op (#1, #2, #3 below)**: `analysis.json` confirms identical
  `mean_dbm=-67.5` across all 3 BEL variants AND the baseline. Numerical evidence
  (not just md5) — 4 identical coverage rasters with distinct BEL parameters.

- **ANTENNA_PRESET=0 suppresses DOWNTILT/BW (#11)**: `analysis.json` confirms
  `mean_dbm=-72.8` for omni, omni+downtilt=6°, and omni+sector=65° — three
  identical rasters.

- **K_FACTOR_PRESET**: The preset IS honored in `report.json` (k=0.67 for
  PRESET=0, k=1.333 for PRESET=2). The `itm_loss_db=127.168` is identical for
  both over the 55 km Manila→Tagaytay path, which is physically plausible (k-factor
  affects diffraction; over this terrain, standard vs sub-refractive atmosphere
  may not diverge measurably for ITM). The PRESET-vs-custom override finding below
  remains correct.

**Behavioral assertion effectiveness**: 4 assertions correctly `xfail` (BEL_ENABLED,
TX_CLUTTER_OVERRIDE, CLUTTER_PERCENTILE, ANTENNA_BW+PRESET) — these paired
comparisons detect zero-delta outputs and self-suppress until the plugin fix lands.
This is the mechanism the roadmap's "expects-error" item below should complement.

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

Surfaced by the revised test harness run (see `### Revised test harness — behavioral
assertion confirmation` above). Distinct from the correctness items above — these are
robustness and developer-experience recommendations.

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

### Updated release shape

Group by category per `AGENTS.md`:
- Security: redirect scheme check, URL redaction, sanitiser whitespace
- Correctness: SAALOS scalar/vector parity, K_FACTOR_PRESET override warning,
  ANTENNA_PRESET vs BW/AZ inconsistency (comparison + coverage), inconsistent
  report JSON key naming, simple-clutter mode BEL/percentile/override silent
  no-op, coverage report.json input echo
- Robustness: backoff jitter, shm finalizer logging, GDAL geometry type warnings, DEM cross-sea timeout
- Testing (runner repo, out of scope for plugin release): expects-error
  mechanism, warning threshold deduplication, mislabeled v4 tests
- Quality-of-life: simple-clutter mode param warnings, coverage report.json input echo, simple vs advanced clutter duality resolution

One PR per category. Manual QGIS UI test not required (no Qt-widget changes).
