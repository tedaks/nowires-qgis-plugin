# Changelog

SPDX-License-Identifier: GPL-3.0-or-later

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned for v1.6.1 (PATCH — bugfix; security → resource leaks → correctness)

- Fix `should_use_multiprocessing(os_name="posix")` returning `False` on macOS hosts. The function checks `sys.platform == "darwin"` unconditionally after the `os_name` branch, so the real platform override defeats the mock. Tests in `test_coverage_engine.py`, `test_macos_process_guard.py`, and `test_coverage_pool_extended.py` must monkeypatch `sys.platform` to `"linux"` when asserting the posix path.
- Add `setWindowFlag` method to mock `QDialog` in `tests/_qgis_mocks.py`. `CoverageOpacityDialog.__init__` calls `self.setWindowFlag(Qt.WindowType.Tool)` on macOS (`coverage/opacity.py:72`), but the stub `QDialog` at line 311-319 lacks the method, causing 9 `AttributeError` failures on darwin.
- Fix `test_plugin_load.py` failures on macOS — `_ensure_gdal_env()` (`__init__.py:87-95`) runs on darwin and calls `QgsApplication.instance()`, which the `_FakeQgsApplication` mock lacks. The test fixture must monkeypatch `sys.platform` to `"linux"` (or mock `_ensure_gdal_env`) so the darwin-specific code path is skipped, matching CI behavior.
- Document local macOS QGIS 4 integration testing setup in `CONTRIBUTING.md`: (1) create `lib/python3.12` symlinks in `Resources/python3.11/` to satisfy PYTHONHOME stdlib layout expectations, (2) re-sign `python3.12` with `disable-library-validation` entitlement, (3) restore `numpy==1.26.4` for QGIS-bundled C extension ABI compatibility, (4) set `PYTHONHOME`, `DYLD_FRAMEWORK_PATH`, `PROJ_LIB`/`PROJ_DATA` pointing to `Resources/qgis/proj` (where `proj.db` lives).
- Fix CSV formula-injection bypass via leading whitespace in `report/export.py::_csv_safe`. Inputs like `" =CMD(...)"` slip past the `s[0] in ('=','+','@','\t','\r')` check because the leading space lands at position 0. Add `s = s.lstrip()` before the formula-character test (the existing `\r`/`\n` replace at line 50 stays). Regression test: a row whose value is `" =1+1"` must serialise with the `'` prefix.
- Add `threading.Lock` around `_pending_releases` mutations and the `_atexit_registered` flag in `shared_dem_grid.py:44-45`. Under `BatchAlgorithm.ALLOW_THREADING = True`, the main process can mutate these concurrently from multiple algorithm threads, leading to torn dict updates or duplicate `atexit` registration. Worker processes are unaffected (spawn-isolated, per the module header comment). One module-level `_releases_lock = threading.Lock()` wrapping the `__setitem__`/`pop` calls in `_create()`/`release()`.
- Skip pre-allocation of `prx_grid`, `loss_grid`, `itm_loss_grid`, `clutter_loss_grid`, `clutter_rx_db_grid`, and `bel_rx_db_grid` in `coverage/engine.py::compute_coverage` when `build_coverage_tasks` returns an empty list. Move the `if not tasks: return None` check above the six `np.full((grid_size, grid_size), nan32, dtype=float32)` calls at lines 122-126. Saves ≈20 MB per empty-coverage run (no pixels within radius) — currently allocated and immediately discarded.
- Fix `dem_downloader.tile_name_for(lat, lon)` raising `ValueError` on float input. The `"{:02d}"`/`"{:03d}"` format specifiers at lines 117-122 require ints. Add `lat, lon = int(round(lat)), int(round(lon))` at the top of the function. All current callers pass `range()` ints, so behavior is unchanged for them; this closes a latent contract bug exposed by any future caller that forwards user-typed coordinates.
- Mask `dist_grid_km` to NaN where `prx_grid` is NaN in `coverage/summary.py:60-71`. The haversine block returns finite distances for every cell, but the `usable_mask` at line 74 only filters by `~np.isnan(prx_grid)` — any downstream consumer that reads `dist_grid_km` without first applying that mask sees clean distances for unusable cells. One line after the haversine: `dist_grid_km = np.where(np.isnan(prx_grid), np.nan, dist_grid_km)`.
- Add `logger.debug("Bilinear sample out of bounds: lat=%s lon=%s", ...)` to `_bilinear._bilinear_scalar` (line 31-32) and equivalent guards in `_bilinear_line` / `_bilinear_grid`. Out-of-bounds samples currently return `nan` silently; downstream blank coverage pixels then get attributed to "missing DEM data" without diagnostic evidence. Debug-level keeps production logs clean while making the failure mode discoverable.
- Fix `KeyError('gain_db')` in `batch/outputs.py:_compute_single_link` — `tx_def["gain_db"]` and `rx_def["gain_db"]` use direct dict access but point-parameter-derived definitions (single TX in One-to-Many mode, single RX in Many-to-One mode) lack the `gain_db` key. Changed both to `tx_def.get("gain_db")` / `rx_def.get("gain_db")`. All links were silently skipped; the existing integration test escaped detection because it only validated file existence, not link-computation results. Regression test in `test_batch_philippines.py` asserts all 8 links compute successfully.
- Add `test_batch_philippines.py` — 10 QGIS integration tests for Batch P2P and Coverage Analysis with real Philippines coordinates (Manila Metro Manila, cross-island: Cebu/Davao/Puerto Princesa/Baguio/Iligan/Iriga). Batch tests cover One-to-Many, Many-to-One, link viability, distance-loss monotonicity, and margin-sort ordering. Coverage tests cover 50 km Manila omni, 30 km Cebu at 1800 MHz, 120° sector antenna, and report structure validation. All run offline via synthetic DEM (no network dependency).
- Add `_patch_dem_download()` helper to `tests/test_batch_philippines.py` — patches `ensure_dem_for_area` in both `NoWires.algorithm.batch` and `NoWires.algorithm.coverage` modules directly. The existing `monkeypatch.setattr(dd_mod, "ensure_dem_for_area", ...)` pattern in `test_qgis_integration_extended.py` is ineffective because the algorithm modules capture the function reference via `from NoWires.dem_downloader import ensure_dem_for_area` at import time.
- Fix broken `monkeypatch.setattr(dd_mod, "ensure_dem_for_area", ...)` in `test_qgis_integration_extended.py` — the 3 existing integration tests (P2P, Coverage, Batch) patch `NoWires.dem_downloader.ensure_dem_for_area`, but the algorithm modules capture the function at import time via `from NoWires.dem_downloader import ensure_dem_for_area`. The tests currently download real Copernicus GLO-30 DEM tiles (explains their 7–15s runtime and network dependency). Replace with `_patch_dem_download()` (or move the helper into `tests/conftest.py` as a shared fixture).
- Add `test_contour_pipeline_integration.py` — full-pipeline QGIS integration test for the contour lines algorithm. Calls `ContourLinesAlgorithm.processAlgorithm()` with a synthetic DEM through all 7 stages (validate AOI → download/merge → smooth → generate contours → reproject → export GPKG → symbology). Existing contour tests either analyze source code via AST/grep or test isolated GDAL calls; no test exercises the complete pipeline end-to-end.
- Add cross-island Many-to-One batch test to `tests/test_batch_philippines.py` — multiple TX candidate sites (Cebu, Davao, Baguio, etc.) transmitting to a single RX in Manila, spanning the full Philippine archipelago DEM extent.
- Fix missing climate context in `batch/writer.py` — `write_batch_json` and `write_batch_csv` omit the climate zone from outputs. Batch results are not reproducible without knowing which ITM climate zone was used. Add `"climate": CLIMATE_NAMES[climate]` to the JSON payload and a `Climate` column to the CSV header. P2P and Coverage reports already include `climate_name`; this closes the batch gap.
- Fix missing climate in `comparison/reporting.py::build_panel_info()` — Coverage Comparison reports omit climate zone for panels A and B, even though each panel has an independent `PANEL_A_CLIMATE` / `PANEL_B_CLIMATE` selection. Add `"climate": CLIMATE_NAMES.get(climate, str(climate))` to the panel info dict to match P2P and Coverage reporting.
- Add climate-variation integration test — all existing integration tests hardcode `CLIMATE: 1` (Continental Subtropical). Add a test with `CLIMATE: 0` (Equatorial) vs `CLIMATE: 6` (Maritime Temperate sea) on the same link, asserting `margin_db` differs measurably between the two extreme climate zones.
- Add `if qgis.utils.iface is None: return` guard at top of `p2p/chart.py::show_profile_chart()` — the function unconditionally dereferences `iface.mainWindow()` and `iface.addDockWidget()`, raising `AttributeError` in headless QGIS (CI, Docker tests, QGIS server). Existing tests avoid the crash path by setting `show_chart=False`, but direct callers are unprotected.
- Add `Climate: <CLIMATE_NAMES[climate]>` line to `p2p/report_display.py::report_p2p_results()` — P2P console feedback prints frequency, polarization, link budget, Fresnel, and status but omits the climate zone. A single line between frequency and polarization would make the output self-documenting.
- Add matplotlib-based P2P chart rendering test — all existing chart tests are unit tests (`build_obstruction_data`, `build_chart_status_text`) or source-code pattern checks (`test_p2p_chart_visibility_draw.py`). No test creates a `matplotlib.figure.Figure`, renders the profile chart, and verifies artists (terrain fill, LOS line, Fresnel envelope, TX/RX markers) exist with correct styles and positions. Can run without QGIS (matplotlib only).
- Add proper offline P2P integration test — `test_p2p_process_algorithm_runs_with_synthetic_dem` in `test_qgis_integration_extended.py` uses the broken `monkeypatch.setattr(dd_mod, ...)` pattern and downloads real DEM tiles. Replace with `_patch_dem_download()` and add assertions on all 4 output layers (profile, Fresnel polygon, Fresnel lines, markers) plus report JSON structure with Philippines coordinates.
- Add full-pipeline Coverage Comparison integration test in Docker — all 5 existing comparison test files are unit tests on isolated functions. No test exercises `CoverageComparisonAlgorithm.processAlgorithm()` end-to-end with dual panels, delta raster generation, and HTML report output. Test with Panel A at 43dBm vs Panel B at 33dBm (otherwise identical, colocated at Manila) should verify delta raster with expected sign and valid improved/degraded pixel counts.
- Validate `PANEL_A_GRID_SIZE == PANEL_B_GRID_SIZE` at parameter-extraction time in `algorithm/coverage_comparison.py` — the check currently runs at line 170 after both expensive panel computations finish. Moving the validation to just after `collect_panel_params()` for both panels would fail fast with a `QgsProcessingException`, saving ~2× coverage computation time when sizes differ.
- Relax `validate_panels()` TX position tolerance in `comparison/reporting.py:44` from `1e-5°` (~1.1 m) to `1e-3°` (~111 m) — map-click precision at typical QGIS zoom levels for 50km-radius coverage analysis is ~0.0001°. The current `1e-5°` threshold effectively requires users to type coordinates manually rather than clicking on the map.
- Fix `assert tmpdir is not None` crash in `comparison/reporting.py:resolve_output_paths()` when all three explicit output paths (`out_a`, `out_b`, `out_delta`) are provided. `tmpdir` is only created when at least one output path is missing (lines 70-71); the unconditional assert at line 72 raises `AssertionError` when all three are user-supplied, crashing the comparison algorithm. Guard the `tmpdir` fallback block with `if tmpdir is not None:`.
- Fix missing ITM finite-loss guard in `batch/outputs.py:_compute_single_link()`. `min(itm_result.loss_db, ITM_LOSS_UPPER_BOUND)` at line 127 is called without checking `itm_result.failed` or `math.isfinite(itm_result.loss_db)`. When ITM returns NaN or Inf, `min(NaN, ...)` produces NaN, silently corrupting the link result. Both `p2p/compute.py:142` (checks `.failed` + `isfinite`) and `coverage/compute.py:109` (checks `isfinite`) already validate before use. Add `if result.failed or not math.isfinite(result.loss_db): return None` guard.
- Fix contour algorithm silently returning `{}` on DEM failure in `algorithm/contour.py:164-167`. When `download_and_merge_tiles()` returns `None`, the algorithm calls `feedback.reportError(...)` then `return {}` — the user receives an empty result dict with no `QgsProcessingException`, making the run appear to succeed with no output and only a log message. Raise `QgsProcessingException("DEM download/merge failed for the selected area.")` instead.
- Fix scalar/vector formula divergence in `clutter/saalos.py` below-canopy path. The scalar path at line 128 computes `math.exp(1.0 / cch__meter - h_tx__meter)` which Python evaluates as `exp((1/cch) - htx)`, matching the ITWOM 3.0 C++ original (`itwom3.0.cpp` line 410: `exp(1/prop.cch-prop.tgh)`) and the Rust upstream (`clutterloss-itm-addon-rust/src/lib.rs` line 186: `(1.0 / cch__meter - h_tx__meter).exp()`). The vectorized path at line 282 computes `np.exp(1.0 / m_cch_h)` where `m_cch_h = np.maximum(cch - htx, 1e-10)`, i.e. `exp(1/(cch-htx))`, which is a fundamentally different expression. The transliteration error arose from substituting the single variable `m_cch_h = max(cch - htx, 1e-10)` for both `(cch - htx)` (the outer multiplier and `q2` linear coefficient, where it is correct) and `cch` alone inside the `exp()` denominator (where it is wrong — the divisor must remain `cch`). The divergence is masked for typical parameters (cch=15 m, htx=5–10 m, d=1 km) where both paths produce ≥22 dB and clip at `MAX_CLUTTER_LOSS`, but produces 2–6 dB error for small-canopy/short-distance cases (cch=0.5 m, htx=0.1 m, d=0.1 m: 3.4 dB) and a complete loss inversion — 0 dB instead of 22 dB — when htx approaches cch (the buggy `exp(1/(cch-htx))` blows up to infinity, making `q1` hugely negative, pushing `arte` below zero, and clipping to 0 dB). Fix line 282 to use `np.exp(1.0 / cch - htx)` (broadcast arrays), matching the scalar, ITWOM, and Rust forms. The `1e-10` clamp on `m_cch_h` remains valid for the outer multiplier; the overflow guard becomes unnecessary since `1.0/cch` cannot overflow for physically valid canopy heights (cch>0 enforced by the early-return guard at line 33). Add below-canopy regression tests with uncapped parameters (d=0.1 m, cch=0.5 m, htx=0.1 m) and a near-canopy divergence test (cch=5.0 m, htx=4.9 m) that would fail with the current vectorized code. Add source-reference comments at lines 126 and 280 documenting the ITWOM/Rust provenance of the below-canopy formula and the note that the `exp()` argument is `(1/cch - htx)`, not `1/(cch-htx)`. The previous description referenced "the SAALOS derivation in the module docstring" — no such docstring exists; the canonical source is the ITWOM 3.0 C++ original.
- Fix `comparison/panel.py:83` raising bare `ValueError` instead of `QgsProcessingException`. User-facing errors from the comparison panel ("Failed to load clutter grid…") produce an unhandled Python traceback instead of the QGIS Processing framework's user-friendly error presentation (which catches `QgsProcessingException`). Replace `ValueError` with `QgsProcessingException`.
- Fix matplotlib figure memory leak in `p2p/chart.py`. The `matplotlib.figure.Figure` is tied to a `QDockWidget` via `WA_DeleteOnClose`, but the `_on_destroy` callback only disconnects the `mpl_connect` handler and blocks checkbox signals — `fig.clear()` and `plt.close(self.fig)` are never called. Repeated P2P analyses cause slow memory accumulation in the matplotlib backend. Add `self.fig.clear()` and `plt.close(self.fig)` (guarded with `contextlib.suppress`) to the destroy path.
- Fix missing `FlushCache()` on the hillshade GDAL dataset in `contour/overlay.py:83-94`. After `gdal.DEMProcessing()` creates the hillshade, `hillshade_result` is set to `None` at line 94 without calling `FlushCache()`. Some GDAL drivers may not fully flush data to disk until explicitly requested. The overview-building code at lines 103-107 correctly calls `FlushCache()` on the update handle, but the initial dataset write is unflushed. Add `hillshade_result.FlushCache()` before `hillshade_result = None`.
- Fix P2P chart failure not surfaced to user in `p2p/compute.py:78-80`. Chart creation exceptions are caught and logged at `logger.warning` level but not pushed to the QGIS Processing feedback. The user sees no visible indication that chart creation failed (the P2P analysis itself succeeds). Add `feedback.pushWarning("P2P profile chart creation failed")` alongside the existing log.
- Fix P.2109-2 `theta_deg` not clamped to validity range in `clutter/p2109_bel.py:68`. ITU-R P.2109-2 specifies 0° ≤ θ ≤ 90° for building entry loss, but the implementation only takes `abs(theta_deg)` without clamping values above 90°, producing unrealistically large `L_e` contributions. Add `theta_deg = max(0.0, min(abs(theta_deg), 90.0))` before computing `L_e`.
- Fix P.2108-1 §3.1 near-zero height producing implausibly large loss in `clutter/p2108_height_gain.py:87,128`. The scalar guard at line 75 checks `h_m <= 0.0` but values very near zero (e.g., 1e-10 m) pass the guard, causing `log10(1e-10 / R) ≈ -11` which produces ~280 dB of loss at 1 GHz via `-Kh2 * log10(...)`. The vectorized path clamps with `np.maximum(h[mask], 1e-30)`, producing ~856 dB. Both outputs are far beyond physical plausibility — `max(0.0, Ah)` only clamps negatives. Add a minimum physical height floor of 0.1 m to both guard conditions so near-zero heights return 0.0.
- Add regression tests for 6 crash/error paths currently untested: (1) `comparison/reporting.py:72` — `assert tmpdir is not None` raises `AssertionError` when all 3 output paths are user-supplied, (2) `batch/outputs.py:127` — missing `isfinite`/`.failed` guard lets NaN/Inf ITM results corrupt link output, (3) `clutter/saalos.py:128` — scalar/vector formula divergence for near-zero `cch` produces different loss values, (4) `clutter/p2109_bel.py:68` — `theta_deg` above 90° not clamped, (5) `clutter/p2108_height_gain.py:87` — near-zero `h_m` near-zero height overflow, (6) 5× `RuntimeError` branches in `contour/generation.py` (lines 45, 55, 87-89, 96, 98-99) for dataset creation/reprojection/export failures.
- Add `processAlgorithm()` end-to-end integration tests for `BatchAnalysisAlgorithm` and `CoverageComparisonAlgorithm`. P2P and Coverage algorithms already have `processAlgorithm()` coverage via `test_qgis_integration_extended.py`, but Batch and Comparison have zero direct testing of their algorithm entry points — the most business-critical code paths.
- Add ~30 error-path tests covering untested `RuntimeError`/`QgsProcessingException` branches across `contour/overlay.py` (3 branches), `p2p/outputs.py` (3), `coverage/pool.py` (2), `raster_io.py` (1), `report/markers.py` (2), `batch/outputs.py` (1), and `macos_compat.py` (1). Group by module to keep test files under 300 lines.
- Add hypothesis property-based tests for uncovered pure-logic numeric functions: `_bilinear.py` (out-of-bounds NaN, boundary coords, sub-pixel stability), `contour/_smoothing_vrt.py::_gaussian_kernel_2d` (normalization, symmetry), `clutter/saalos.py` (scalar == vectorized agreement), `clutter/p2108_*` and `p2109_bel.py` (boundary values for height, theta, distance, frequency), `nan_utils.py` (leading/trailing/all-NaN patterns), `geo_bounds.py` (antimeridian wrap, extreme latitudes). One file: `tests/test_hypothesis_numeric.py`.
- Add multiprocessing execution smoke test — one test that runs `ProcessPoolExecutor`-based ITM on a tiny grid (2×2) and verifies sequential and parallel results match. All current MP tests use `FakeExecutor` or `monkeypatch`, never spawning real workers.
- Add climate-variation integration test — same link with climate=0 (Equatorial) vs climate=6 (Maritime Temperate), assert `margin_db` differs measurably. All existing integration tests hardcode `CLIMATE: 1`.


### Planned for v1.7.0 (PATCH — tech-debt / cleanup, zero behavior change)

- Rename the project's `coverage/` subpackage (suggest `coverage_analysis/`) to stop shadowing the installed `coverage` pip package. From the project root, `import coverage` resolves to the empty [coverage/__init__.py](coverage/__init__.py), so `python -m coverage` and `python -c "import coverage"` both break (`No module named coverage.__main__` / `AttributeError: module 'coverage' has no attribute 'Coverage'`). CI escapes the bug only because `.venv/bin/pytest` and `.venv/bin/coverage` put the script directory at `sys.path[0]` instead of cwd, so pytest-cov's `import coverage` hits the pip package and caches it in `sys.modules`; `python -m pytest --cov` or `python -m coverage run` from a fresh checkout fail. The `a1_coverage.pth` workaround present in some local venvs is gated on `COVERAGE_PROCESS_START` and is not committed to the repo. Rename touches the 14 modules under `coverage/`, every `from coverage.` / `import coverage.` caller, the `[tool.coverage.run] omit` entry in `pyproject.toml:31`, plus the import-linter, mypy, and AGENTS.md references.
- Extract `safe_create_dir(target, parent=None)` to a new `fs_utils.py` and call it from both `dem_downloader.get_temp_dir` (lines 67-114) and `worldcover_downloader._safe_create_dir` (lines 66-111). The two functions implement near-identical symlink/TOCTOU mitigation (`O_DIRECTORY | O_NOFOLLOW` check, `tempfile.mkdtemp` + `os.rename` pattern, `0o700` chmod) with only the create-path divergence (`makedirs` vs `mkdtemp`). Consolidation prevents a future security patch landing in only one of the two files.
- `.gitignore`: add `.env`, `*.pem`, `*.key`, `credentials*`, `*.zip`, and `**/*.prj` (the existing `/*.prj` only matches the repo root, not nested projection files dropped by GIS output). Defense-in-depth against accidental secret commits; no code risk.
- `.github/workflows/release.yml`: gate the `release` job on a green test run. The workflow currently builds and uploads the QGIS plugin zip on every `v*.*.*` tag without running pytest, so a broken tag publishes. Either inline `pytest -q -m "not benchmark and not qgis_integration and not gdal_integration"` as a prerequisite step or refactor `tests.yml` to `workflow_call` and add `needs: [test]`.
- `.github/workflows/integration.yml:42`: gate `qgis-integration` on `tests.yml` success instead of only its own internal `lint` job. Today both workflows run in parallel; an integration run on a commit whose unit tests fail wastes ~20 min of container time and produces confusing red/green CI status. Use `workflow_run` triggered by `tests.yml` completion, or `workflow_call` from a parent workflow.
- Wire `antenna.clear_pattern_cache()` into `antenna_pattern_preview.py` so selecting a new pattern CSV during a session invalidates the `_read_pattern_points` `lru_cache(maxsize=32)`. The public API already exists at `antenna.py:168` and the cache docstring at line 148-150 already documents the limitation; only the call site at the pattern-picker is missing.
- `.github/workflows/tests.yml:67-68`: `pip-audit --requirement constraints-ci.txt` audits only the 9 pinned direct deps. Transitive dependencies — where most CVEs land — are not audited. Generate a full lockfile (`pip-compile --generate-hashes` from a `requirements.in` covering runtime + test + lint + typecheck) and run `pip-audit` against that. Roll into the existing audit job.
- `.importlinter`: add forbidden-import contracts beyond the single `itm-no-qgis` rule. After the v1.6.0 subpackage reorganization (`algorithm/`, `batch/`, `comparison/`, `contour/`, `coverage/`, `clutter/`, `p2p/`, `report/`), the intended layering between subpackages is unenforced. Grep current imports first to encode the actual dependency graph rather than aspirational rules that fail on day one.
- Switch `algorithm/batch.py:182` from manual construction + `try/finally: elev.close()` to `with ElevationGrid(dem_path) as elev:` so it matches `algorithm/coverage.py:220`. Both paths already close the grid correctly (the existing `try/except` at 184-186 and `finally` at 256-261 handle failures); this is a consistency change, not a leak fix. Reviewer-trap elimination only.
- `.github/workflows/tests.yml:144`: the explicit `--cov-fail-under=0` looks like the coverage gate is disabled. It isn't — `fail_under = 59` in `pyproject.toml:39` is picked up by pytest-cov on the appended-coverage step at line 147 (where `--cov-fail-under` is omitted; pytest-cov falls back to the coverage config). Add an inline comment explaining the split, or move the threshold to the CLI of the final step so the number is grep-able from the workflow file. No behavior change either way; reviewer-trap elimination only.
- `.github/workflows/integration.yml:38`: remove the duplicate `ruff check .` job — the same check already runs in `tests.yml:38`. Once integration gates on tests (above), the duplicate is redundant. Saves ~30s of runner time per PR.
- Rename `coverage/pool.py::_dynamic_chunk_size` → `_compute_chunk_size`. The function returns `_MIN_CHUNK_SIZE` (64) for every `n_tasks <= 1024` — for typical coverage runs (192×192 = 36864 tasks rare; sub-1024 common after radius masking) it behaves as a step function, not a continuous dynamic policy. Update the docstring to lead with the floor behavior.
- `metadata.txt`: add `homepage=`, `repository=`, `tracker=` keys. Confirm the public-repo URL before committing — do not fabricate one.
- `pyproject.toml`: tighten `numpy>=1.20` → `numpy>=2.0` in `[project.optional-dependencies].dev`. The `requires-python = ">=3.12"` constraint already implies numpy 2.x (numpy 1.x has no 3.12 wheel); the looser lower bound only misleads readers.
- `constraints-ci.txt`: pin `import-linter==2.11.x` (currently `==2.11` — the only entry in the file without a patch version, breaking the file's own convention).
- Bundle parameter explosion into frozen dataclasses. `compute_coverage` carries 35 params, `build_p2p_report_payload` carries 35, `build_coverage_report_payload_for_grid` carries 31. Most natural groupings (`AntennaConfig`, clutter bundle, link budget, BEL settings) already exist; the work is wiring them through.
- USERS-GUIDE.md: align clutter category naming. Line 313 uses `rural` in the simple-mode table; line 346 uses `Open rural / Dense rural`. The codebase's `clutter/categories.py` is the source of truth — pick whichever key it actually exposes and apply consistently across the doc.
- Centralize shared test helpers (`_create_synthetic_dem`, `_write_point_gpkg`, `_patch_dem_download`) from `tests/test_batch_philippines.py` into `tests/conftest.py` or a new `tests/_test_helpers.py`. Currently duplicated or will be needed across multiple integration test files (batch Philippines, contour pipeline, existing qgis_integration_extended).
- Harden `CLIMATE_OPTIONS` ordering in `constants.py:21` — `CLIMATE_OPTIONS = list(CLIMATE_NAMES.values())` relies on dict insertion order matching the integer keys 0-6. Replace with an explicit `[CLIMATE_NAMES[i] for i in range(len(CLIMATE_NAMES))]` so the mapping remains correct even if `CLIMATE_NAMES` gains out-of-order keys. Add `assert list(CLIMATE_NAMES.keys()) == list(range(7))` to `test_constants_and_defaults.py`.
- Fix CCH override treating explicit 0.0 as "no override" in `comparison/params.py:168` and `shared_params.py`. `cch_override_m > 0.0` treats `0.0` as `None`, preventing users from forcing zero canopy clutter height when it's physically justified (e.g., bare-earth sites). Use a sentinel value or `Optional[float]` with `None` as the "not set" marker.
- Centralize remaining magic numbers not yet covered by existing constants. `-32768` (DEM nodata) is used in 6 modules (`contour/smoothing.py`, `contour/pipeline.py`, `contour/overlay.py`, `contour/generation.py`, `dem_downloader.py`, `contour/_smoothing_vrt.py`) but has no shared definition (contrast `COVERAGE_NODATA = -9999.0`). `32.45` (FSPL constant) in `p2p/compute.py`, `1e6` (MHz-to-Hz) in `fresnel.py` and `radio.py`, `0o700` (directory permissions) in `dem_downloader.py`, `temp_manager.py`, and `worldcover_downloader.py`, and `4.0 / 3.0` (k-factor) in `fresnel.py`, `radio.py`, `batch/analysis_params.py`, and `defaults.py` all lack centralized definitions. `EARTH_RADIUS_M` (6371000.0), `METERS_PER_DEGREE_LAT` (111320.0), and `BYTES_PER_MEBIBYTE` (1048576.0) already exist in `constants.py` but are not consistently used at all call sites (`analyze_coverage.py`, `package_gpkg.py`, `export_portable.py`, `run_coverage.py` still use bare literals).
- Narrow overly broad `except Exception:` clauses at 7 sites to specific exception types. Affected locations: `constants.py:49` → `except (ImportError, RuntimeError)` (WGS84 CRS import), `shared_dem_grid.py:129` → `except (BufferError, ValueError, OSError)` (shm copy), `p2p/compute.py:79` → `except (ImportError, RuntimeError)` (chart display), `p2p/compute.py:253` → `except OSError` (clutter grid close), `coverage/pool.py:123,139` → `except OSError: pass` (shm close), `algorithm/batch.py:183,210` → `except (OSError, RuntimeError)` (ElevationGrid creation/grid close), `temp_manager.py:77` → `except (ImportError, OSError)` (macOS temp dir).
- Add missing type annotations to ~30 public functions in `elevation.py`, `dem_downloader.py`, `radio.py`, `shared_params.py`, `cache_manager.py`, and `p2p/chart.py`. These modules collectively define the plugin's core data model and propagation contracts; incomplete annotations force downstream callers to suppress mypy errors.
- Establish project-wide error type policy for invalid input. `radio.py` raises `ValueError`, `elevation.py` raises `RuntimeError`, and algorithm modules raise `QgsProcessingException` — no consistent rule governs which type signals validation failure vs. runtime error. Define the policy (e.g., `ValueError` for parameter validation, `QgsProcessingException` for user-facing processing failures, `RuntimeError` for internal state errors) and document in `CONTRIBUTING.md`.
- Add GPL-3.0-or-later copyright headers to `export_portable.py` and `export_project.py` (both entirely missing — only a shebang and module docstring). `raster_io.py` has the `Copyright` + `SPDX-License-Identifier` lines but lacks the full GPL boilerplate block comment present in all other source files.


### Planned for v1.7.0 (MINOR — additive features)

- Extend PDF report output (`OUTPUT_REPORT_PDF`) from Coverage Analysis to Point-to-Point Analysis and Coverage Comparison. The shared `report.pdf.write_report_pdf()` writer is already in place; remaining work is parameter registration and `_write_*_outputs` wiring in `algorithm.p2p` and `algorithm.coverage_comparison`.
- Promote the standalone "Preview Antenna Pattern" dialog into an inline `QgsProcessingParameterWidgetFactoryInterface` so the polar plot renders directly in the Coverage / P2P parameter dialog next to the pattern-file picker.
- Audit `report.pdf.write_report_pdf()` for paged-table behaviour on long reports — current implementation lets `QTextDocument` decide page breaks. Resolve before or during PDF parity work.
- Add a radio preset library. Today every `tx_power` / `rx_sens` / `f_mhz` / `polarization` value is typed by hand from a vendor datasheet. Mirror the existing `ANTENNA_PRESETS` pattern in `antenna.py:84-90`: add a `RADIO_PRESETS` dict in a new `radio_presets.py` keyed by manufacturer + model, each entry a frozen dataclass (`label`, `f_mhz_min`, `f_mhz_max`, `tx_power_options_dbm`, `rx_sens_dbm`, `polarization`, `notes`). Add a `RADIO_PRESET` enum parameter to P2P, Batch, Coverage, and Coverage Comparison; selecting one populates the relevant numeric fields. Seed the library with the most common tactical / commercial radios (e.g. L3Harris RF-7800V-HH, AN/PRC-152, Motorola APX, Tait TM9400, Codan Envoy). Optionally extend with a `*.radio.json` drop-in folder so users can add their own without code changes. Skip PDF-parsing approaches — datasheet layouts vary enough between vendors that regex/heuristic extraction fails silently in dangerous ways for engineering work; LLM-based extraction is out of scope for the plugin runtime. Pre-flight grep on `tx_power` / `rx_sens` to ensure no callers bypass the new dialog flow; this touches the parameter-registration surface so it's a MINOR bump.
- Add per-link climate zone override in Batch P2P Analysis — `_features_to_points()` in `algorithm/batch.py:50-69` already extracts per-feature `height`, `gain_db`, `antenna_preset`, and `azimuth` from the point layer. Add `climate = _feat_attr(feat, "climate", None)` with fallback to the global climate default. `_compute_single_link()` would use the per-link climate via `tx_def.get("climate")` or `rx_def.get("climate")`. Enables mixed-climate batch analysis (coastal vs. inland RX sites in different ITM climate zones) without rerunning the algorithm separately per zone.

## [1.6.0] - 2026-05-19

### Refactor

- Internal module layout reorganized into 8 subpackages
  (algorithm/, batch/, comparison/, contour/, coverage/, clutter/, p2p/,
  report/). 60 modules relocated; zero behavior changes. All imports
  switched to absolute (`NoWires.X`).
- Architectural import rule enforced by import-linter: ITM module
  must not depend on qgis or PyQt.
- **NOTE FOR USERS:** Restart QGIS after upgrading. Do not use Plugin
  Reloader, which retains references to deleted flat modules and will
  raise ImportError on first invocation post-upgrade.

## [1.5.12] - 2026-05-18

### Changed

- Extract `build_link_clutter_context()` factory in `clutter_context.py`, consolidating the 14-field `ClutterLossContext` construction duplicated in `p2p_compute.run_p2p_analysis` and `batch_outputs._compute_single_link`. Duck-types over `P2PAnalysisParams`/`BatchAnalysisParams`; `tx_h`/`rx_h` remain explicit since batch overrides per-link from feature attributes. Companion to existing `build_initial_clutter_context()` for the placeholder (distance=0, rx_ground=0) case used by coverage.
- Replace inline Fresnel/earth-bulge/LOS reimplementation in `batch_outputs._compute_single_link` with a call to the existing `fresnel.fresnel_profile_analysis`. The two implementations were mathematically equivalent (per-point first-Fresnel radius, k-factor earth bulge, linear LOS interpolation); the inline version was a parallel maintenance burden. Removes the unused `EARTH_RADIUS_M` import from `batch_outputs.py` and the redundant `tx_h_eff_actual` alias. `clearance_pct` continues to use the strict `> 0` semantic by computing from `terrain_bulge`/`los_h`/`fresnel_r` returned by the helper.
- Switch `comparison_panel.run_panel_coverage` from inline `ClutterLossContext(distance_m=0.0, rx_ground_elevation_m=0.0, ...)` construction to the existing `build_initial_clutter_context()` factory in `clutter_context.py`. Same placeholder-context pattern already used by `algorithm_coverage._build_clutter_context` and `coverage_engine._build_clutter_context`; consolidates the third call site. `tx_ground_elevation_m=0.0` is passed explicitly to preserve current behavior (sampling TX ground from the elevation grid here would be a separate fix, not a refactor).
- Extract `ComparisonPanelParams` frozen-shape dataclass and `collect_panel_params()` factory in `comparison_params.py`. Moves the ~90-line `parameterAsDouble/Enum/File/Bool` block out of `run_panel_coverage` into a single typed bundle covering all 39 panel fields plus derived values (`clutter_enabled`, `clutter_model`, `bel_building_type`, `cch_override_m`, `antenna_bw_override`). `run_panel_coverage` drops from 227 lines to ~107 lines; `comparison_panel.py` from 276 lines to 163. Caller-visible behavior unchanged.
- Consolidate the `tx_def["height"] if tx_def["height"] is not None else params.tx_h` resolution in `batch_outputs._compute_single_link` to a single `tx_h_eff` local at the top of the function. Previously the same ternary appeared three times (lines 95, 109, 131 of the pre-cleanup file) with two different aliases (`tx_h_eff` / `tx_h_actual`).

### Added

- Added `test_collect_panel_params.py` — 13 unit tests covering `comparison_params.collect_panel_params()`. Stubs `parameterAsDouble/Enum/File/Bool` with a fake algorithm object so the tests run as plain unit tests (no `qgis_integration` marker). Locks in the per-field dataclass mapping, prefix handling, and the derivation rules for `clutter_enabled`, `clutter_model`, `cch_override_m`, `bel_building_type`, `antenna_az` (conditional on `antenna_bw < 360`), and `antenna_bw_override` (the custom-preset escape clause).
- Added 4 tests to `test_clutter_context.py` covering the new `build_link_clutter_context()` factory: full-field mapping from the params duck-type, per-link `dist_m` independent of params, explicit `tx_h`/`rx_h` overriding any params attribute, plus a guard test on `build_initial_clutter_context()`'s placeholder semantics (`distance_m=0`, `rx_ground_elevation_m=0` regardless of caller input).
- Register `comparison_params` in `tests/_qgis_mocks.py` `_PACKAGE_SUBMODULES` so unit tests can import it through the `NoWires` package machinery without the `qgis_integration` marker.
- Added `test_clutter_math_snapshot.py` — 32 drift-guard snapshot tests covering `p2108_height_gain.height_gain_loss`, `p2108_terrestrial_stat.clutter_loss_p2108_terrestrial_stat`, `p2109_bel.building_entry_loss`, and `clutter_saalos.clutter_loss_saalos`. Pins a small grid of (inputs → output) tuples per module and asserts `math.isclose` with `rel_tol=1e-9`. Expected values are self-captured from the current implementation, so the tests catch accidental coefficient drift between releases; spec compliance is still the job of the existing per-module property tests.

## [1.5.10] - 2026-05-17

### Fixed

- Fix `AttributeError: module 'os' has no attribute 'geteuid'` on Windows. `_cleanup_stale_shared_memory()` called `os.geteuid()` unconditionally, which is POSIX-only and crashes on Windows where `/dev/shm` doesn't exist. Guard with `hasattr(os, "geteuid")` and skip cleanup on non-POSIX platforms. Skip the `/dev/shm` cleanup scoping regression test module on non-POSIX platforms via `pytestmark = pytest.mark.skipif(not hasattr(os, "geteuid"), ...)`.
- Fix P2P profile chart checkbox toggles having no visible effect. `update_visibility()` called `art.set_visible()` on chart artists but never called `fig.canvas.draw_idle()` to trigger a repaint. Unchecking Terrain, LOS, Fresnel, 60% Band, or Antennas appeared to do nothing until the user triggered an unrelated repaint (mouse hover, window resize). Add `fig.canvas.draw_idle()` after the artist-visibility loop in the deferred callback so toggles take effect immediately.
- Fix latent `NameError` in P2P profile chart visibility toggle when `tx_marker`/`rx_marker` are undefined. `tx_marker` and `rx_marker` are only created when `len(los_h) > 0` but `update_visibility()` references them unconditionally. Initialize both to `None` and skip them in the toggle loop when `None`.
- Fix `AttributeError` when `P2PAnalysisParams.tx_antenna_config` or `rx_antenna_config` is `None` (the dataclass default). `antenna_gain_adjustment_db` accesses `config.preset` without a null check, crashing on `NoneType`. The report-payload path (lines 227–228) correctly guards with a ternary; the gain-calculation path (lines 164–166) does not. Return 0.0 dB adjustment when either config is `None`.
- Fix clutter grid resource leak on early exception in `run_p2p_analysis`. The `clutter_grid.close()` call sits in a `finally` block at line 258 that only covers output writing (lines 195–257). If `ensure_dem_for_area` fails, the terrain profile is too short, all elevations are NaN, or ITM prediction fails (lines 108–142), the `finally` is never reached and the `LandCoverGrid` numpy array persists until GC — significant in long-running QGIS sessions with large land-cover rasters. Move the try/finally to encompass the whole section from clutter-grid acquisition onward.
- Fix Fresnel zone longitude overflow across antimeridian in `write_fresnel_zone`. Interpolated `lon = tx_lon + t * dlon` can exceed ±180° when the path crosses ±180° (e.g., `tx_lon=179, rx_lon=-170` produces `lon=184.5` at `t=0.5`), creating invalid WGS84 coordinates. Wrap interpolated longitudes to [-180, 180] after computing `lon`.
- Fix `_ChartCanvas.closeEvent` being dead code in P2P profile chart. The canvas is a child widget embedded in the dock layout; Qt only delivers `closeEvent` to top-level widgets, so the override never fires. The `mpl_disconnect` tooltip cleanup and `blockSignals` calls are never reached. Move cleanup to the `QDockWidget` close event or use `destroyed` signal.
- Fix `dock.setFloating(True)` called before `addDockWidget` in P2P profile chart. `setFloating` has no effect when the dock is not yet in a `QMainWindow`; on some platforms the chart appears briefly docked before floating. Reorder to `addDockWidget` first, then `setFloating(True)`.
- Fix `build_obstruction_data` sorting by terrain height instead of Fresnel penetration deficit. `peaks.sort(key=lambda i: terrain_bulge[i])` ranks the tallest peaks rather than the most obstructive ones (highest `terrain_bulge - (los_h - fresnel_r)`). When there are more than 5 obstructions, the most penetrative peaks may be omitted from annotations. Sort by deficit instead.
- Fix `_p2p_outputs_internal._write_p2p_output_layers` not returning `fresnel_lines_path`. The function writes the Fresnel lines file but omits it from the return tuple. The caller in `p2p_compute.py` reconstructs the path from `fresnel_poly_path` using the same naming convention, which is a DRY violation. Return the path directly.
- Fix `k_factor` and `wavelength_m` input validation in Fresnel calculations. `fresnel_radius` validates `d1_m`/`d2_m` but not `f_mhz` (zero/negative causes `ZeroDivisionError` or `ValueError`). `fresnel_profile_analysis` and `earth_bulge` don't validate `k_factor` (zero causes silent `inf`/`nan` arrays in NumPy; negative produces physically meaningless negative bulge). Add early-return guards for `f_mhz <= 0` and `k_factor <= 0`.
- Fix `build_obstruction_data` docstring claiming returns `(index, deficit)` tuples when it actually returns 6-element tuples `(idx, d_km, terrain_bulge, los_h, fresnel_r, deficit)`.

### Added

- Added `test_p2p_chart_visibility_draw.py` — regression tests for P2P chart visibility toggle repaint, marker NameError guard, dock destroyed signal cleanup, and addDockWidget/setFloating ordering.
- Added `test_antenna_none_config.py` — regression test for `antenna_gain_adjustment_db` None config guard.
- Added `test_p2p_clutter_grid_leak.py` — regression test for clutter grid resource leak on early exception.
- Added `test_p2p_outputs_lon_wrap.py` — regression test for Fresnel zone longitude overflow across antimeridian.
- Added `test_obstruction_deficit_sort.py` — regression test for `build_obstruction_data` deficit sort and 6-element tuple docstring.
- Added `test_p2p_output_layers_fresnel_lines_path.py` — regression test for `_write_p2p_output_layers` returning `fresnel_lines_path` in 4-tuple.
- Added `test_fresnel_input_validation.py` — regression test for `f_mhz` and `k_factor` validation guards in Fresnel calculations.

### Changed

- SHA-pin `github/codeql-action/init` and `github/codeql-action/analyze` in `codeql.yml` (previously `@v4` major-version tags; all other workflows already use SHA digests per project policy in AGENTS.md).
- Add `needs: [lint]` gate to `integration.yml` so the QGIS Docker job is skipped when cheap checks fail, avoiding ~20 min of wasted runner time.
- Remove unused `qt_dialog` pytest marker from `pyproject.toml` marker declarations; `test_pyqt_dialogs.py` uses `skipif`, not the marker.
- Add `pip check` step after `pip install --break-system-packages --ignore-installed` in `integration.yml` to verify the QGIS container dependency tree is not broken by constraint overrides.
- Extract conftest QGIS mock setup from `tests/conftest.py` (495 lines) into `tests/_qgis_mocks.py` to keep conftest focused on fixtures and improve maintainability of mock stubs.
- Convert `release.yml` zip manifest from exclusion-based `git ls-files | grep -vE` filtering to an explicit include list, preventing accidental inclusion of new dev-only directories.

## [1.5.9] - 2026-05-17

### Fixed

- Fix `tile_download_base.download_tile_with_retry` purging structurally-valid cached tiles when `ComputeStatistics` fails. The stats read was treating any `RuntimeError` or `None` return as corruption, triggering an unnecessary re-download. Cache hits now validate only structural integrity (`gdal.Open() is not None`, `RasterCount >= 1`, non-zero dimensions); actual pixel-data corruption is caught at use-time, and the per-tile wall-clock budget covers runaway downloads.
- Fix `dem_downloader.download_tiles` and `worldcover_downloader.download_worldcover_tiles` false-tripping their overall wall-clock deadlines (300s / 600s) on legitimately-large coverage areas. The per-tile budget added in v1.5.3 (`DEFAULT_PER_TILE_WALL_CLOCK_BUDGET = 180s` in `tile_download_base`) already caps per-tile runaway; the overall deadlines did not scale with tile count and aborted healthy multi-tile runs. Both removed.

### Added

- Added `test_tile_cache_stats_tolerance.py` — regression test for cache-hit on `ComputeStatistics` failure with intact structural integrity.
- Added `test_downloader_no_overall_deadline.py` — regression test for full processing of a large tile list with no overall-deadline check in either downloader.

## [1.5.8] - 2026-05-17

### Changed

- Decompose `coverage_pool.py` (300→276 lines): extract `apply_batch_results` and `log_coverage_failures` into `_coverage_result_dispatch.py`.
- Decompose `p2p_compute.py` (300→265 lines): extract `_write_p2p_output_layers` and `_write_p2p_reports` into `_p2p_outputs_internal.py`.
- Decompose `contour_smoothing.py` (300→195 lines): extract Gaussian kernel, raster calc, and blur VRT helpers into `_smoothing_vrt.py`.
- Replace hardcoded `111320.0` in `algorithm_coverage.py` and `algorithm_coverage_comparison.py` with `METERS_PER_DEGREE_LAT` from `constants.py`.
- Replace `f_mhz: float = 300.0` defaults in `CoverageAnalysisParams` and `BatchAnalysisParams` with `DEFAULT_FREQ_MHZ` from `defaults.py`.
- Replace `N0=301.0, epsilon=15.0, sigma=0.005` in `coverage_engine.compute_coverage` with `DEFAULT_N0`, `DEFAULT_EPSILON`, `DEFAULT_SIGMA` from `defaults.py`.
- Add `SMOOTHING_NONE`, `SMOOTHING_LOW`, `SMOOTHING_MEDIUM`, `SMOOTHING_HIGH`, `SMOOTHING_OPTIONS` constants in `contour_smoothing.py`; replace string literals in `algorithm_contour.py` parameter registration.
- Add `DELTA_STYLE_DIVERGING` and `DELTA_STYLE_THRESHOLD` constants in `comparison_params.py`; replace string literals in `comparison_outputs.py`.
- Add `CLUTTER_OVERRIDE_AUTO` constant in `clutter.py`; replace `"Auto"` string comparisons.
- Collapse `SharedDEMGrid._atexit_cleanup` into class-level alias on `release`; eliminates duplicate logic.
- Convert silent `except … pass` in `shared_dem_grid.py` close/release/unlink paths to `logger.debug`; narrow `except Exception` to `except OSError`.
- Drop duplicate `ProcessPoolExecutor` re-export from `coverage_engine.py`; all runtime usage and monkeypatching lives in `_coverage_executor.py`.
- Add `gdal_integration` pytest marker for tests that require numpy-2-compatible GDAL bindings; exclude from host unit-test run, include in QGIS Docker integration run.
- Add `WGS84_CRS` singleton to `constants.py`; replace 6 inline `QgsCoordinateReferenceSystem("EPSG:4326")` constructions across `algorithm_p2p`, `algorithm_batch`, `algorithm_contour`, `algorithm_coverage_comparison`, `comparison_panel`, `coverage_params`.
- Move `FRESNEL_60PCT_FACTOR` from `defaults.py` to `constants.py`; update import sites in `fresnel.py`, `p2p_outputs.py`, `p2p_chart.py`.
- Add `EMPTY_MARGIN_DB = -999.0` to `constants.py`; replace magic literal in `report_payloads.py`.
- Replace 3 hardcoded `1048576.0` literals in `nowires.py` and `cache_manager.py` with `BYTES_PER_MEBIBYTE` from `constants.py`.
- Convert remaining 7 silent `except … pass` sites to `logger.debug`: `nowires.py` (3 sites), `three_d.py`, `p2p_chart.py`, `temp_manager.py`, `processing_utils.py`. Narrow `except Exception` to `except OSError` where safe (shared memory, temp dir).
- Add `from __future__ import annotations` to 7 clutter/p2108 modules (`clutter_categories`, `clutter_constants`, `clutter_resolve`, `clutter_saalos`, `p2108_common`, `p2108_terrestrial_stat`, `p2109_bel`) for consistency with sibling modules.
- Replace `last_contour_layer_id` string literal at `three_d.py:79` with `CONTOUR_LAYER_KEY` constant.
- Reconcile sequential-mode notice in `_coverage_executor.py` with MP-fallback message: `"Using single-threaded mode..."` → `"Single-threaded mode: no multiprocessing detected"`.
- Replace `# type: ignore[arg-type]` cluster in `comparison_reporting.py` with explicit `assert tmpdir is not None`; removes three type-ignore suppressions.
- Break `clutter.py` ↔ `clutter_advanced.py` import cycle: move `TerminalClutterLosses` from `clutter.py` to `clutter_context.py`, eliminating the deferred-import workaround.
- Extract a single shared bilinear sampler into `_bilinear.py` (`bilinear_sample`, `bilinear_sample_grid`, `bilinear_sample_grid`), consolidating four re-implementations in `ElevationGrid.sample`, `ElevationGrid.sample_line`, `ElevationGrid.sample_grid`, and `sample_line_from_grid`.
- Promote underscore-private clutter symbols to public API: `_ClutterComponents` → `ClutterComponents`, `_compute_advanced_loss` → `compute_advanced_loss`, `_resolve_category_advanced` → `resolve_category_advanced`; move `legacy_to_advanced_override` from `clutter_resolve.py` to `clutter_categories.py`.
- Improve `worldcover_class_to_clutter_category` out-of-range handling: early-return `"open"` for invalid class IDs instead of `% 256` fallthrough.
- Wrap `document.print(printer)` in `report_pdf.write_report_pdf` in try/except with `logger.debug` and `return False` on failure.
- Add module description to `nowires.py`.
- Single-source per-category P.2108 parameters: derive `p2108_height_gain._CATEGORY_PARAMS` from `clutter_categories.CLUTTER_CATEGORY_PARAMS` instead of duplicating `R_m` and method tags.
- Convert stringly-typed enums to `typing.Literal`: add `ClutterModel = Literal["simple", "advanced"]` and `BuildingType = Literal["traditional", "thermally_efficient"]` in `clutter_context.py`; update type annotations across all call sites.
- Replace length-tag dispatch `isinstance(result, tuple) and len(result) == 2 and result[0] == "error"` in `_coverage_result_dispatch.py` with `WorkerError` frozen dataclass sentinel.
- Move `_warned_low_vhf_p2108_combined` global mutable flag into `_P2108State` dataclass in `clutter_resolve.py`; tests can reset via `_STATE.warned_low_vhf = False`.

### Added

- Added `test_p2108_category_params_derived_from_clutter_categories.py` — consistency test verifying `_CATEGORY_PARAMS` in `p2108_height_gain` is derived from `CLUTTER_CATEGORY_PARAMS`.
- Added `test_worker_error_sentinel.py` — regression test for `WorkerError` dataclass sentinel replacing length-tag dispatch.

## [1.5.7] - 2026-05-17

### Fixed

- Fix haversine numerical stability in `coverage_summary._compute_grid_summary` — add `a = np.clip(a, 0.0, 1.0)` before `2 * R * np.arcsin(np.sqrt(a))` so FP rounding at antipodal or near-zero distances no longer yields NaN distances.
- Replace `assert self.data is not None` with `RuntimeError` in `ElevationGrid.sample`, `sample_line`, and `sample_grid`. `assert` is a no-op under `python -O`; an explicit raise is always enforced and much easier to diagnose than a silent NaN read after `close()`.
- Fix `algorithm_batch.processAlgorithm` unconditionally closing the user-supplied clutter grid. Add `owns_clutter_grid` flag to `BatchAnalysisParams` and `_collect_batch_inputs` (set True only when auto-downloaded); gate the close in `processAlgorithm` on that flag, mirroring `p2p_compute.py:133-137,294-298`.
- Fix `coverage_pool._init_cov_pool` re-registering `_final_cov_pool` on every initializer call. Gate `atexit.register` with a module-level `_cov_pool_atexit_registered` flag so the finalizer is registered exactly once even across worker reinit.
- Fix `_coverage_executor.execute_coverage_tasks` discarding partial multiprocessing counters when the pool raises and falls back to sequential. Accumulate (`pixels_failed += seq_failed`, `pixels_done += seq_done`) rather than reassign.
- Fix GDAL dataset leak in `contour_pipeline.download_and_merge_tiles` clip verification. Replace bare `gdal.Open(fn_clip) is None` with explicit `test_ds = gdal.Open(fn_clip); ...; test_ds = None` pattern matching `tile_download_base.py:143-154`.
- Fix `NoWiresPlugin.run_pattern_preview` antenna-preview dialog leak. Declare `_pattern_preview_dialog = None` in `__init__`, close-then-replace on each invocation, and close in `unload()` — mirroring the `_opacity_dialog` lifecycle.
- Clamp `geo_bounds.coverage_bounds` results to valid lat range `[-90, 90]` and replace local `meters_per_deg_lat = 111320.0` with `METERS_PER_DEGREE_LAT` from `constants.py`.
- Fix `coverage_params._add_pct_params` using `DEFAULT_TIME_PCT` for all three percentage parameters. Split the loop so each `addParameter` call references its matching default (`DEFAULT_TIME_PCT`, `DEFAULT_LOCATION_PCT`, `DEFAULT_SITUATION_PCT`).
- Fix `contour_overlay.py:103-106` releasing hillshade dataset without flushing pyramid overviews. Add `hillshade_ds.FlushCache()` before `hillshade_ds = None`.
- Fix `algorithm_contour.py:96-97` leaking permanent temp directory when `get_temp_dir()` returns None. Route the fallback `tempfile.mkdtemp` through `TempDirManager.add_dir` for cleanup.
- Fix `ElevationGrid.__init__` zero-division on degenerate DEM rasters. Raise `RuntimeError` when `n_rows == 0` or `n_cols == 0` before computing `d_lat` / `d_lon`.
- Fix `summarize_coverage_grid` zero-division on empty grids. Return the zero-count summary dict early when `n_rows == 0` or `n_cols == 0`.
- Fix `SharedDEMGrid._create` atexit-handler pinning `self` and `shm`. Replace bound-method `atexit.register(self._atexit_cleanup)` with module-level `_pending_releases` weak-reference dict and `_atexit_release_pending` handler; add `__del__` safety-net so abandoned segments are released promptly.

### Added

- Added `test_haversine_clip.py` — regression test for haversine numerical stability.
- Added `test_elevation_runtime_error.py` — regression test for `assert` → `RuntimeError` in ElevationGrid.
- Added `test_batch_owns_clutter_grid.py` — regression test for batch clutter-grid ownership flag.
- Added `test_pool_atexit_gating.py` — regression test for atexit re-registration gating.
- Added `test_executor_partial_counters.py` — regression test for partial counter accumulation on MP fallback.
- Added `test_contour_pipeline_clip_leak.py` — regression test for GDAL dataset leak in clip verification.
- Added `test_pattern_preview_dialog_leak.py` — regression test for antenna-preview dialog lifecycle.
- Added `test_hillshade_flush_cache.py` — regression test for FlushCache before hillshade release.
- Added `test_contour_tempdir_cleanup.py` — regression test for fallback temp-dir cleanup registration.
- Added `test_shared_dem_atexit_weakref.py` — regression test for weak-reference atexit registry in SharedDEMGrid.
- Added `test_geo_bounds_lat_clamp.py` — regression test for lat clamping and METERS_PER_DEGREE_LAT import.
- Added `test_elevation_zero_div_guard.py` — regression test for zero-rows/cols RuntimeError guard.
- Added `test_coverage_summary_zero_div_guard.py` — regression test for empty-grid zero-division guard.
- Added `test_coverage_pct_param_defaults.py` — regression test for separate percentage parameter defaults.

## [1.5.6] - 2026-05-17

### Fixed

- Fixed `_pickle.PicklingError: Can't pickle <function _init_cov_pool at 0x...>: it's not the same object as NoWires.coverage_pool._init_cov_pool` on Windows multiprocessing. The error surfaced on Windows after the v1.5.5 `pythonw.exe` switch made `find_windows_python_executable()` succeed where it had been silently returning `None` on user setups — so the multiprocessing branch ran for the first time and exposed a latent bug.

  Root cause: `_coverage_executor.py` did `from .coverage_pool import _init_cov_pool, _itm_worker_batch` at module-import time, freezing those names as references to the function objects from the *first* import of `coverage_pool`. If anything subsequently replaced `NoWires.coverage_pool` in `sys.modules` — QGIS plugin reload, the "Plugin Reloader" plugin, any manual `importlib.reload` of just that one file — `sys.modules["NoWires.coverage_pool"]._init_cov_pool` became a new function object, but `_coverage_executor._init_cov_pool` still pointed at the old one. `pickle`'s identity check (`getattr(sys.modules[fn.__module__], fn.__qualname__) is fn`) then failed when `ProcessPoolExecutor` tried to serialize the initializer to send to the spawned worker.

  Fix: resolve both `_init_cov_pool` and `_itm_worker_batch` through `from . import coverage_pool as _cp` *inside* `execute_coverage_tasks`, so each call walks `sys.modules` fresh and the function references handed to `ProcessPoolExecutor` are guaranteed identical to what `pickle` finds by name. The module-level `from .coverage_pool import ...` line no longer carries those two names.

### Changed

- Changed the multiprocessing-fallback diagnostic in `_coverage_executor.execute_coverage_tasks` from `feedback.pushInfo("Multiprocessing unavailable, using single-threaded mode...")` to `feedback.pushWarning("Multiprocessing unavailable ({}: {}), using single-threaded mode...".format(type(exc).__name__, exc))`. Previously, when the MP branch raised, the exception type and message were emitted only via Python `logger.warning`; on GUI-subsystem QGIS builds (Windows `pythonw.exe`-bundled, some macOS configurations) the `StreamHandler` can have `stream=None` and silently drop the message — leaving the user with an opaque "Multiprocessing unavailable" with no trail back to the underlying cause. Routing the exception details through the QGIS Processing feedback channel keeps future regressions self-diagnosing in the log panel.

### Added

- Added `tests/test_coverage_executor_reload_pickle.py` — three regression tests that lock in the lazy-lookup contract: (1) after `importlib.reload(coverage_pool)`, the function objects passed to a fake `ProcessPoolExecutor` must be `is`-identical to the reloaded module's attributes; (2) `pickle.dumps` on the reloaded `_init_cov_pool` / `_itm_worker_batch` must succeed (mirrors what `ProcessPoolExecutor` does on spawn); (3) source-level check that `_coverage_executor.py` does not import either symbol at module scope ahead of `execute_coverage_tasks`. Verified the first and third fail without the fix and pass with it.

### Documentation

- `Technical_Documentation.md`: expanded the "Multiprocessing in QGIS" and "Coverage Engine Robustness" sections with the function-local-import contract, the underlying pickle identity-check failure mode, and how v1.5.5's `pythonw.exe` detection unmasked the previously-latent bug on Windows.

## [1.5.5] - 2026-05-16

### Fixed

- Fixed coverage multiprocessing silently falling back to sequential mode on macOS via **three distinct bugs** that all surfaced as `feedback.pushInfo("Multiprocessing unavailable, using single-threaded mode...")` with the actual exception logged only via Python `logger.warning` (often invisible in the QGIS UI).

  **(1) macOS POSIX shared-memory name too long.** `shared_dem_grid.SharedDEMGrid._create()` was generating names of the form `nowires_dem_<20 hex>` (32 chars). macOS XNU defines `PSHMNAMLEN = 31` as the maximum length including the leading `/` that `multiprocessing.shared_memory.SharedMemory` prepends, so the actual limit after the slash is 30 chars. Names of 32 chars + leading slash = 33 chars triggered `OSError: [Errno 63] File name too long` at `SharedMemory(create=True, name=...)`. Linux's `NAME_MAX = 255` hid this. Fix: truncate the UUID hex suffix from 20 to 16 chars (28 chars total, 29 with slash; comfortably under the macOS limit).

  **(2) Spawn-mode cross-process cancel signal abandoned.** Even with the shm name fix, the next step in the pipeline used a plain `multiprocessing.Event()` in `_coverage_executor.execute_coverage_tasks`. Under the `spawn` start method (macOS default, Windows, containers), the Event's internal Condition raises `RuntimeError: Condition objects should only be shared between processes through inheritance` when `pool.map` tries to pickle it. An interim fix using `multiprocessing.Manager().Event()` worked in Docker but died on the user's macOS QGIS with `EOFError` (the Manager subprocess couldn't be sustained in that environment). The fix that actually works: **remove the cross-process cancel signal entirely**. Cancellation now comes from the main thread breaking out of `pool.map` between batches; in-flight batches finish naturally (~64 tasks × ~5 ms ≈ 320 ms worst case at default chunk size). Linux `fork` was masking both issues.

  **(3) QGIS-bundled `python3.12` aborts on spawn because `sys.prefix` is baked to a CI-builder path.** After (1) and (2) were fixed, workers started spawning but died immediately with `ModuleNotFoundError: No module named 'encodings'` and `Fatal Python error: init_fs_encoding: failed to get the Python codec of the filesystem encoding`. The macOS QGIS-final 4.0.2 build ships a `python3.12` binary whose `sys.prefix` is hard-coded to `/Users/runner/work/QGIS/QGIS/build/vcpkg_installed/arm64-osx-dynamic-release/` (the CI builder's path). QGIS itself overrides this internally via `Py_SetPythonHome()`, but spawned children get no such override and can't find the stdlib. Surfaced as `BrokenProcessPool: A child process terminated abruptly`. Fix: `macos_compat.configure_macos_multiprocessing()` now sets `os.environ["PYTHONHOME"] = sys.prefix` (the *running* interpreter's prefix, which QGIS has remapped to a valid path like `Contents/Frameworks/`). Spawned workers inherit the env at spawn time and find the QGIS-bundled stdlib. Also added a `_can_spawn()` validation step in `find_macos_python_executable()` so we never return a binary that can't actually boot — and an `NOWIRES_PYTHON_EXE` env var override for users who want to point at a different Python (e.g. Homebrew).

  Measured speedup on the in-container `benchmarks/coverage_runtime.py`: small grid 6840 → **31038 px/s** (4.5×), medium grid 7318 → **44024 px/s** (6.0×), large grid 7416 → **48207 px/s** (6.5×). macOS users will see equivalent gains.

### Changed

- Added a Windows mirror of `configure_macos_multiprocessing` / `find_macos_python_executable` in a new `windows_compat.py`. `_can_spawn` is shared between the two via `from .macos_compat import _can_spawn`. The Windows helper looks for `pythonw.exe` first, then `python.exe`, in standalone and OSGeo4W-style bundle layouts (`<qgis>/pythonw.exe`, `<qgis>/../apps/Python3X/pythonw.exe`, `<qgis>/bin/pythonw.exe`, etc.), validates each candidate by actually launching it under a prepared env (`PYTHONHOME=sys.prefix`), and honours the `NOWIRES_PYTHON_EXE` env var as an explicit override. `pythonw.exe` is preferred so spawned workers don't pop a stray cmd window each (`python.exe` is a console-subsystem binary; `pythonw.exe` is the same interpreter without a console — pipe-based stdin/stdout/stderr still works, which is all `multiprocessing` uses).
- Replaced the v1.5.3-era `NOWIRES_WINDOWS_MP=1` opt-in env-var gate with the validating helper above. Windows multiprocessing is now self-adjusting: if `find_windows_python_executable()` returns a working interpreter, multiprocessing is on; otherwise the executor cleanly falls back to sequential with a clear log message.
- Removed cross-process cancel signaling from coverage multiprocessing entirely. `_itm_worker_batch` now takes a plain batch argument (no `(batch, event)` tuple) and the executor no longer creates an `Event` or `Manager`. Trade-off: cancel responsiveness drops from per-pixel to per-batch (~320 ms worst case for a 64-pixel batch at ~5 ms ITM/pixel).

### Added

- Added `tests/test_coverage_executor_spawn_safety.py` — 3 source-level contract tests asserting the executor does NOT use `multiprocessing.Event()` or `multiprocessing.Manager()`, and that `_itm_worker_batch` takes a plain batch argument. Catches regression to either of the broken patterns without needing a fork/spawn test harness.
- Added `tests/test_shared_dem_grid_name_length.py` — contract test that parses the literal name template in `shared_dem_grid.py` and asserts the total length (`/<prefix><N hex>`) stays under `PSHMNAMLEN = 31`. Future edits that lengthen the prefix or extend the hex suffix will fail loudly.

## [1.5.4] - 2026-05-16

### Fixed

- Fixed macOS `SIGABRT` crash when running Coverage Analysis with `ALLOW_THREADING` enabled. Previously `processAlgorithm` called `show_coverage_legend()` (which constructs and `.show()`s a `QFrame`) inline; with the v1.5.3 threading opt-in this ran on a `QThreadPool` worker, and Cocoa rejects `QWidget` creation off the main thread (`abort()` from `_initWithContentRect:`). The legend now stashes its `rx_sensitivity_dbm` on the algorithm instance during `processAlgorithm` and is shown from `postProcessAlgorithm`, which the QGIS Processing framework guarantees runs on the main thread. Linux/Xlib tolerated this pattern; macOS did not.

### Changed

- Extracted `_validate_dem_coverage` from `algorithm_coverage.py` to a new `coverage_dem_validate.py` helper module to keep `algorithm_coverage.py` within the 300-line cap after the new `postProcessAlgorithm` override.

### Added

- Added `tests/test_coverage_legend_deferred.py` — source-level contract tests asserting the legend show is deferred to `postProcessAlgorithm`. Catches regressions that would re-introduce the macOS crash without needing a real QGIS UI run.

## [1.5.3] - 2026-05-16

### Added

- Added `write_report_pdf()` PDF report writer (`report_pdf.py`) using Qt6 `QTextDocument` + `QPrinter`. Wired to Coverage Analysis as a new `OUTPUT_REPORT_PDF` output. Falls back to a warning and returns `False` when Qt print-support isn't available rather than raising.
- Added `AntennaPatternPreviewDialog` (`antenna_pattern_preview.py`) and a "Preview Antenna Pattern" plugin menu action. Loads an antenna pattern CSV and renders a polar plot via `QPainter` — no matplotlib dependency.
- Added `extract_link_budget_params()` and `LinkBudgetBundle` in `shared_params`. Companion to `extract_clutter_params` introduced earlier; deduplicates the 5-double link-budget extraction across `algorithm_p2p`, `algorithm_batch`, and `coverage_params`.
- Added `build_initial_clutter_context()` factory in `clutter_context.py`. Single source of truth for the placeholder `ClutterLossContext(distance=0, rx_ground=0)`; previously constructed inline in both `algorithm_coverage._build_clutter_context` and `coverage_engine._build_clutter_context`.
- Added `NOWIRES_WINDOWS_MP` environment variable to opt Windows into multiprocessing (off by default). `_ensure_path()` already handles the sys.path hardening needed for spawn-mode workers.
- Added `build_html_document()` in `report_export.py` to share the HTML body between HTML and PDF writers.
- Added golden-file regression tests for CSV/JSON/HTML report output (`tests/test_report_export_golden.py`). Catches accidental drift in field names, escape rules, or document structure.
- Added `tests/test_report_pdf.py` — unit test for the Qt-unavailable fallback path plus a qgis_integration test that asserts a real PDF is written.

### Changed

- Refactored `nowires.py` plugin GUI registration to a single `action_specs` table; removed nine duplicated `QAction(...)` blocks. Net –50 lines and easier to add new menu actions.
- Switched `contour_smoothing.py` from monkey-patching `xml.etree.ElementTree.parse = _safe_parse` (which globally mutated the stdlib parser for every importer in the process) to an explicit `_parse_xml()` wrapper.
- Vectorized the elevation-sampling fallback in `coverage_engine._build_rx_ground_grid` via row-by-row `sample_line` calls when `sample_grid` isn't available; 192× fewer Python-level calls at the default grid size for mocked elevation grids.
- Increased sequential coverage progress reporting from 100 buckets to 200 (`_coverage_executor._run_sequential`).
- HTTP retryable and non-retryable failures in `tile_download_base.download_tile_with_retry` now surface status code and retry timing through `feedback.pushInfo` / `pushWarning`; previously these only went to the Python log.
- `_init_cov_pool` no longer raises `RuntimeError("Shared-memory pool already bound")` when a worker is reused across runs — resets stale state and rebinds instead. Friendlier when threading is enabled.
- Added one-line reason comments to every previously-unexplained `# type: ignore` in production source (9 sites).

### Added (previously in 1.5.3)

- Added `ALLOW_THREADING` opt-in on `NoWiresAlgorithm`. Coverage Analysis, Batch P2P, and Coverage Comparison opt their `processAlgorithm()` into the Processing framework's worker-thread runner so the QGIS UI stays responsive during long computations; quick algorithms (P2P, Contour) keep the existing `NoThreading` behaviour.
- Added `DEFAULT_PER_TILE_WALL_CLOCK_BUDGET` (180s) default for `download_tile_with_retry`. Caps the total time spent retrying a single DEM or WorldCover tile so a slow trickle (where `socket_timeout` never fires) cannot stall a coverage run for `socket_timeout × max_retries` seconds.
- Added `get_cache_size()` and `format_cache_size()` to `cache_manager`. The "Clear DEM Cache" menu now reports current cache size and asks for confirmation before deleting.
- Added `ClutterParamBundle` plus `extract_clutter_params()` in `shared_params`. Single helper replaces three ~20-line duplicated extraction blocks in `algorithm_p2p`, `algorithm_batch`, and `coverage_params`.
- Added `test_algorithm_threading_optin.py` source-level contract tests verifying which algorithms opt into threading.
- Added `TestGetCacheSize` tests for the new cache-size helpers.

### Changed

- Increased coverage multiprocessing progress update frequency from every 50 chunks to every 5 chunks (`_coverage_executor.py`) for finer UI feedback.
- Refactored `clear_dem_cache()` to share the `_iter_cache_entries()` + `_entry_size()` helpers used by `get_cache_size()`, removing duplicated glob/walk loops.

## [1.5.2] - 2026-05-15

### Added

- Added `clear_pattern_cache()` API for reloading antenna pattern CSV files without QGIS restart
- Added GDAL `UseExceptions()` at plugin startup for consistent error handling across all GDAL operations
- Added batch algorithm multipart geometry handling with debug logging
- Added contour CRS fallback to EPSG:4326 when context project is unavailable
- Added NaN-aware elevation interpolation in batch P2P computation using `nan_utils`
- Added 8 new test suites: algorithm execution integration, base algorithm integration, raster I/O integration, hypothesis property-based tests for antenna, coverage compute, Fresnel, and radio
- Added CI pipeline: `pytest` on Python 3.12, `pip-audit` dependency scanning, `ruff` lint in integration job, `timeout-minutes` on benchmarks, version/changelog enforcement workflow
- Added concurrency groups with `cancel-in-progress` to all GitHub Actions workflows
- Added two-step pytest isolation in CI: sensitive tests run separately to avoid module state pollution

### Fixed

- Fix `METERS_PER_FOOT` constant incorrectly applied as multiplier for feet-to-meter conversion in contour generation
- Fix missing trailing newlines and import ordering in multiple modules
- Fix mypy compliance: added type annotations to `_geo_utils`, `batch_outputs`, `base_algorithm`, `clutter_advanced`, and 15+ other modules
- Fix dead code removal: unused module-level globals in `coverage_pool`, unused parameters in `coverage_engine`
- Fix CI pipeline: tracked missing `mypy.ini` to prevent type-check failure on checkout
- Fix CI integration job: `continue-on-error: true` removed so QGIS failures now block PRs
- Fix CI integration matrix: removed `release-3_34` (project targets QGIS 4 / Qt 6 only)
- Fix CI integration job: removed redundant explicit test steps already covered by `-m qgis_integration`
- Fix coverage configuration: override `fail_under` to 0 in integration job to avoid false failures from partial integration-only coverage

### Changed

- Integration tests now collect coverage data alongside unit tests for combined analysis
- Updated CONTRIBUTING.md with CI pipeline documentation and local check instructions

## [1.5.1] - 2026-05-12

### Added

- Added "Clear DEM Cache" menu action to remove stale downloaded DEM and WorldCover tiles from the temp directory
- Added `cache_manager.py` module with size-aware cache cleanup
- Added test coverage for `cache_manager.py` (9 tests)

### Fixed

- Fix clutter grid ownership: user-provided land-cover rasters are no longer closed by the algorithm after use (auto-downloaded grids are still cleaned up)
- Fix duplicated numpy scans in coverage report display — statistics are now read from the precomputed report payload
- Fix missing `from __future__ import annotations` in `elevation.py` for Python 3.9 compatibility
- Fix coverage pool module-level globals: removed unused `_cov_pool_id`/`_cov_pools` dead code, replaced with concise comment
- Fix unused `rx_sens` parameter in `write_coverage_raster()` — parameter removed from signature and call sites
- Fix duplicate imports in `clear_dem_cache()` function body
- Fix unused `QMessageBox` import in `nowires.py`
- Fix `algorithm_contour.py`: added fallback when `get_temp_dir()` returns None
- Fix `comparison_add_params.py`: extracted `_add_panel_advanced_params()` helper to keep file under 300-line limit
- Fix `coverage_pool.py`: made `_MAX_WORKERS` computation lazy via `_get_max_workers()` function
- Fix misleading test name `test_handles_broken_symlinks` renamed to `test_handles_readonly_files`

- Fix Qt6 crash when toggling obstruction visibility in P2P chart (Windows access violation)
- Fix Coverage Comparison silently ignoring advanced clutter controls (percentile, street width, BEL, building type, elevation angle)
- Fix P2P output geometries drawn wrong across the antimeridian (±180°)
- Fix `_owns_clutter` UnboundLocalError masking real DEM errors in coverage algorithm
- Fix coverage TX marker not persisting across QGIS sessions — now uses fixed path under user temp dir
- Fix P2P output layers (profile, fresnel, markers) not persisting across QGIS sessions
- Add `_vector_layer_ids` initialization to CoverageAlgorithm for proper layer reordering
- Add `get_temp_dir` stub to P2P compute test for dem_downloader mock
- Defensive `len()` for QGIS layer tree children in base_algorithm

### Changed

- `.gitignore`: added `.coverage` to tracked patterns
- Persistent output paths: coverage and P2P layers now write to fixed directory under user temp dir


## [1.5.0] - 2026-05-07

### Added

- Added "Advanced clutter correction" mode: saalos vegetation model, ITU-R P.2108 for built/rural categories
- Added saalos vegetation clutter model (Python port of ITWOM 3.0 ClutterLoss by Sid Shumate, via the MIT-licensed clutterloss-itm Rust crate). See NOTICE.md for the full MIT license text.
- Added ITU-R P.2108-1 §3.2 statistical clutter loss for terrestrial paths (combined urban+suburban model, 0.5–67 GHz, percentile-based, distance-capped at 2 km)
- Added ITU-R P.2108-1 §3.1 height-gain terminal correction (per-category, 0.03–3 GHz, methods 2a/2b)
- Added ITU-R P.2109-2 building entry loss (two-lognormal model with elevation angle, per building type)
- Added per-category model dispatch per the P.2108/P.2109 compliance design: `none` (open), `p2108_height_gain` (open_rural, dense_rural), `saalos` (vegetation), `p2108_combined` (suburban, urban with §3.1+§3.2 overlap max)
- Added `CLUTTER_PERCENTILE` parameter (0.01–99.99) for P.2108 §3.2 and P.2109 BEL
- Added `STREET_WIDTH_M` parameter (5–100 m, default 27) for P.2108 §3.1
- Added `BEL_ENABLED` boolean parameter for P.2109 building entry loss
- Added `BEL_BUILDING_TYPE` enum (Traditional / Thermally-efficient) for P.2109
- Added `BEL_ELEVATION_ANGLE` parameter (0–90°, default 0) for P.2109
- Added `method`, `percentile`, `tx_bel_db`, `rx_bel_db`, `total_with_bel_db` fields to `TerminalClutterLosses`
- Added `p2108_common.py` — shared Q⁻¹ and F⁻¹ inverse normal CDF implementations with sign-convention guard tests
- Added `p2108_height_gain.py` — P.2108-1 §3.1 height-gain terminal correction (scalar + vectorized)
- Added `p2108_terrestrial_stat.py` — P.2108-1 §3.2 statistical clutter loss (scalar + vectorized)
- Added `p2109_bel.py` — P.2109-2 building entry loss (scalar + vectorized)
- Added `R_m`, `p2108_3_1_method`, `p2108_3_2_applicable` fields to `CLUTTER_CATEGORY_PARAMS`
- Added `percentile`, `street_width_m`, `bel_enabled`, `bel_building_type`, `bel_elevation_angle_deg` to `ClutterLossContext`
- Added `clutter_method` and `clutter_percentile` to P2P report payload
- Added `bel_rx_db` to P2P report payload
- Added `clutter_method` field to `TerminalClutterLosses` for reporting which sub-model fired (e.g. `"§3.1+§3.2/saalos"`)
- Added total path loss computation including BEL: `total_with_bel_db = total_loss_db + rx_bel_db`
- Added comprehensive test suites for p2108_common (24 tests), p2108_terrestrial_stat (14), p2108_height_gain (14), p2109_bel (10)

### Changed

- **Breaking**: Replaced the simplified per-category `clutter_loss_p2108` with proper ITU-R P.2108-1 §3.2 statistical model. Urban/suburban clutter loss values will differ significantly from the previous approximation (which was incorrect).
- **Breaking**: `CLUTTER_CATEGORY_PARAMS` no longer has `base_loss_db` or `model="p2108"`. Use `R_m`, `p2108_3_1_method`, `p2108_3_2_applicable`, and `model="p2108_height_gain"` / `"p2108_combined"` instead.
- P2P analysis now passes `ClutterLossContext` to the advanced clutter dispatch, including antenna height, distance, frequency, and polarization for saalos and P.2108
- P2P total path loss now uses `total_with_bel_db` (includes BEL when enabled)
- Coverage engine caches the TX terminal clutter loss and reuses it across all coverage pixels when using advanced mode
- Coverage per-pixel loop now adds P.2109 building entry loss to RX clutter when `BEL_ENABLED=True`
- Batch and comparison workflows now propagate advanced clutter context and canopy height overrides through their parameter pipelines
- `clutter_p2108.py` is now a deprecation shim that delegates to `p2108_terrestrial_stat` with a `DeprecationWarning`
- Advanced clutter mode now dispatches per-category per-frequency per §6 of the compliance design:
  - open → 0 dB
  - open_rural / dense_rural → P.2108 §3.1 height-gain (f < 3 GHz)
  - vegetation → SAALOS (unchanged)
  - suburban / urban → P.2108 §3.1 + §3.2 combined (max of both in 0.5–3 GHz overlap; §3.2 only above 3 GHz)
- Coverage comparison now propagates BEL parameters through its parameter pipeline

### Fixed

- Fix `ModuleNotFoundError: No module named 'clutter_constants'` at QGIS runtime — `clutter_saalos.py` used absolute import instead of package-relative import
- Fix coverage heatmap missing color near transmitter — palette had no stop above -60 dBm, so strong-signal pixels (> -60 dBm) rendered as transparent in Discrete shader mode. Added "Very Strong" (-30 dBm) stop and a +100 dBm ceiling entry so values up to +100 dBm are covered by the Very Strong color interval.
- Fix P2P owned clutter grid not closed after sampling, preventing GDAL dataset handle leak
- Fix TOCTOU race conditions in temp directory creation
- Fix four stale contract tests that diverged from actual implementation
- Remove four unused imports flagged by ruff
- Fix GDAL handle leak in coverage shared clutter grid cleanup
- Fix NaN dedup logic in coverage summary
- Add safety net `__del__` handlers in `temp_manager.py` and `nan_utils.py` for resource cleanup
- Fix macOS multiprocessing compatibility: prevent duplicate QGIS windows and fix Python executable path
- Fix P.2108 frequency factor: unify all categories to use the same diffraction-based scaling where clutter loss increases with frequency, consistent with P.2108-1 §3.1 Eq. (2f) and §3.2
- Fix coverage pool falling back to sequential mode on worker errors instead of propagating exceptions
- Fix duplicate `compute_terminal_clutter_losses` call in coverage pipeline
- Fix ElevationGrid edge-registered pixel offset and dead globals cleanup
- Fix import of `fresnel_profile_analysis` from `fresnel` module instead of `radio`
- Fix string constant names in comparison `add_clutter_params` instead of `getattr`
- Fix 14 code review issues: resource leaks, metric consistency, API correctness
- Comprehensive macOS compatibility fixes for multiprocessing and GUI

## [1.4.0] - 2026-05-03

### Added

- Batch P2P Analysis algorithm: one-to-many and many-to-one link computation, results ranked by link margin, with combined output layer and optional CSV export
- Coverage Comparison algorithm: dual-panel coverage analysis producing a delta raster (Panel A – Panel B in dB) with statistics and optional report
- Interactive P2P profile chart with hover callouts, Fresnel zone toggle, and chart export
- P2P report and marker outputs (vector layers for TX/RX markers)
- Coverage report outputs (CSV/JSON/HTML)
- Reliability outputs: fade-margin classes, formal-or-fallback availability guidance in P2P and coverage reports
- Live coverage opacity slider dialog (plugin menu action)
- 3D scene tracking and opening for coverage and contour outputs (disabled on Windows)
- P2P rule-based symbology for Fresnel zone, line, and profile layer outputs
- Shared parameter registration (`shared_params.py`), shared DEM grid management (`shared_dem_grid.py`)
- Shared GeoTIFF writer (`raster_io.py`)
- macOS multiprocessing compatibility (`macos_compat.py`)
- NaN-safe array utilities (`nan_utils.py`)
- Temp directory manager with cleanup safety net (`temp_manager.py`)

### Changed

- Architecture refactor: algorithm files split from monoliths over 1000 lines into focused helper modules (coverage, contour, batch, p2p)
- Coverage helper code split by responsibility: `coverage_compute.py`, `coverage_palette.py`, `coverage_legend.py`, `coverage_summary.py`, `coverage_reporting.py`, `coverage_analysis_params.py`
- Contour code split: `contour_generation.py`, `contour_overlay.py`, `contour_pipeline.py`, `contour_smoothing.py`, `contour_symbology.py`
- P2P code split: `p2p_analysis_params.py`, `p2p_params.py`, `p2p_compute.py`, `p2p_outputs.py`, `p2p_chart.py`, `p2p_chart_format.py`, `p2p_symbology.py`, `p2p_report_display.py`
- Comparison code split: `comparison_add_params.py`, `comparison_params.py`, `comparison_panel.py`, `comparison_outputs.py`, `comparison_reporting.py`
- Batch code split: `batch_analysis_params.py`, `batch_params.py`, `batch_outputs.py`, `batch_writer.py`
- Clutter code split: `clutter.py`, `clutter_advanced.py`, `clutter_categories.py`, `clutter_constants.py`, `clutter_context.py`, `clutter_p2108.py`, `clutter_saalos.py`
- Constants extracted into `constants.py` and `defaults.py`
- Base algorithm class extracted into `base_algorithm.py`
- P2P batch constant registration collapsed into dict comprehension
- Comparison panel constants auto-generated in `comparison_params.py`

### Fixed

- **CR3**: Fix VRT Gaussian smoothing being a silent no-op. `root.iter("Source")` never matched `SimpleSource`/`ComplexSource` tags, so the Gaussian kernel was never injected into the VRT. Contour smoothing now works as intended.
- **CR4**: Fix comparison delta math: add COVERAGE_NODATA→NaN normalization and shape guard in `compute_delta_summary` to prevent -9999 sentinel values from being treated as real data.
- **CR5**: Move `QgsProject.instance().writeEntry` calls from `processAlgorithm` to `postProcessAlgorithm` in `base_algorithm.py` to avoid mutating project state inside the processing algorithm.
- **CR6**: Remove dead `_cleanup_cov_pool` function; cap `n_workers` at `_MAX_WORKERS` (16) in coverage engine.
- **CR7**: Fix `unload()` AttributeError by initializing `_toolbar_actions` and `_opacity_dialog` in `__init__`; add `getattr` guards for action removal.
- **CR8**: Fix URL redirect validation from substring prefix check (`startswith`) to `urlsplit().netloc` comparison to prevent URL spoofing.
- Fix FSPL constant: `32.44` → `32.45` in `p2p_compute.py` to match ITU-R P.525 and the ITM internal constant.
- Add RX cable loss to received power calculation (was only subtracted at TX).
- Add NaN count warning in coverage pool worker when replacing NaN elevations with 0.0.
- Change `itm_p2p_loss` exception sentinel from `999.0` to `NaN` with `failed=True` flag to prevent downstream calculations from treating failures as real values.
- Fix CSV injection in report export: sanitize cell values starting with `=`, `+`, `-`, `@`, tab, or CR.
- Fix JSON NaN output in report export: sanitize NaN/Inf values before `json.dump` with `allow_nan=False`.
- Fix copy-paste defaults: `LOCATION_PCT` and `SITUATION_PCT` now use `DEFAULT_LOCATION_PCT` and `DEFAULT_SITUATION_PCT` instead of `DEFAULT_TIME_PCT` in batch params, comparison params, and P2P params.
- Fix `_feat_attr` boolean-vs-int dispatch: check `isinstance(default, bool)` before `isinstance(default, int)`.
- Add `super().unload()` call in `NoWiresProvider.unload()`.
- Fix comparison reporting: return NaN percentages instead of misleading 0.0% when valid_count is zero.
- Add `pushWarning` with error summary when raster layers are invalid in coverage and comparison algorithms.
- Initialize `clutter_grid = None` before try block in `algorithm_coverage.py` to prevent `UnboundLocalError`.
- Fix `gdal.Translate` NoData remap: use `gdal.Warp` with `srcNodata`/`dstNodata` when source NoData differs from target, preventing -9999 elevations from dominating Gaussian blur.
- Add `COVERAGE_NODATA` normalization in `coverage_summary.py` to handle reloaded GeoTIFFs.
- Add `f.flush()` + `os.fsync()` before `os.replace()` in tile download to prevent torn files on power loss.
- Add temp directory permission check in `dem_downloader.py` after `os.makedirs`.
- **Note on NC1/NC2**: Verified as correct behavior, not bugs — the ITM smooth-earth fallback sign and polarization branch both match the NTIA reference implementation.

## [1.3.0]

### Added

- Antenna presets (omni, sector 90/120, dish 20, custom), front-to-back ratio, downtilt, and optional horizontal/vertical pattern CSV support for both P2P and coverage workflows.
- Optional simple terminal clutter correction with WorldCover-style land-cover sampling; clutter loss components (`clutter_tx_db`, `clutter_rx_db`, `total_path_loss_db`) are now visible in all report payloads.
- `worldcover_downloader.py`: ESA WorldCover 2020 v100 tile download, caching, and clip/merge (mirrors the DEM downloader pattern).
- `clutter_source_label()` helper for descriptive clutter source labels in reports.
- `compute_terminal_clutter_losses()` helper for consistent terminal clutter loss computation.
- Coverage report payloads now include `itm_loss_db`, `clutter_tx_db`, `clutter_rx_db`, and `total_path_loss_db` fields.
- P2P clutter grid download now occurs after the bounding box is computed, ensuring the correct area is covered.

### Changed

- Clutter source in P2P and coverage reports is now produced by `clutter_source_label()` instead of a raw file path or inline conditional.
- Coverage clutter reporting now uses the TX terminal clutter loss as the representative `clutter_tx_db` and derives `clutter_rx_db` from the grid-wide mean totals.

### Removed

- The obsolete Qt compatibility helper module has been removed; source now uses QGIS 4 / Qt 6 APIs directly.

### Fixed

- **NC1**: Guard `smooth_earth_diffraction` and `height_function` against `ValueError` from `log`/`log10` on non-positive arguments. When low frequency × small ground impedance causes `K > 1.607`, `B_0` can go negative, which previously crashed the ITM prediction for vertical polarization at 20 MHz over high-conductivity ground. Now returns a large finite loss value consistent with the extreme diffraction regime.
- **NC2**: Add per-task exception handling in `_itm_worker_batch` so a single bad pixel no longer kills an entire chunk of coverage tasks. Broaden the `ProcessPoolExecutor` fallback `except` clause from specific exception types to `Exception`, so `ValueError` and `TypeError` also trigger the sequential fallback with diagnostic logging.
- **NI1**: Add a shared `multiprocessing.Event` for cancellation signalling between the coverage engine and worker processes, reducing cancellation latency from chunk-sized (5–50 s) to task-sized.
- **NI2**: Add `_final_cov_pool()` to close per-worker shared-memory handles on pool shutdown, preventing resource leaks on platforms where OS cleanup is not immediate.
- **NI3**: Extract the -9999 NoData sentinel into a named constant `COVERAGE_NODATA` with documentation explaining why NaN is not used (GDAL Float32 compatibility) and why -9999 is safe.
- **NI4**: Remove unused `TYPE` field from the contour line layer in `algorithm_contour.py`; `gdal.ContourGenerate` never populates it and no downstream code references it.
- **NI5**: Fix `_feat_attr` silent type coercion in `algorithm_batch.py`. `int(float(val))` now logs a warning on truncation, and coercion failures log the attribute name, value, and target type instead of silently falling back to the default.
- **NI6**: Both DEM and WorldCover downloaders now honour the HTTP `Retry-After` header on 429/503 responses, using the server-suggested wait time instead of fixed exponential backoff.
- **NI7**: Socket timeout values in both downloaders extracted into named constants (`_SOCKET_TIMEOUT`) for visibility. A `_WALL_CLOCK_TIMEOUT` constant documents the intended total-per-tile timeout as a contract for future enforcement.
- **NM9**: Add 38 ITM reference-vector tests covering `smooth_earth_diffraction` edge cases (NC1 regression), propagation primitives, and end-to-end `predict_p2p` scenarios across all climate zones, boundary frequencies, and polarization modes.
- Fix Qt 6 `QAction` import location and keep source checks for direct Qt 6 enum usage.
- Fix P2P clutter grid download bounding box: WorldCover tiles are now fetched after the padded TX–RX extent is known, preventing zero-area downloads when the TX and RX are close together.

## [1.2.0]

- Remove `gdal_calc.py` (dead code with `eval()` usage and deprecated `optparse`).
- Fix critical import bug in `report_payloads.py` — bare `from reliability import` would crash at QGIS runtime.
- Vectorize `coverage_summary.py` distance computation for significant speedup on large grids.
- Replace fragile VRT string manipulation in `algorithm_contour.py` with proper XML parsing.
- Use namedtuples for coverage task tuples to prevent fragile positional unpacking.
- Remove global GDAL configuration side effects from `dem_downloader.py` that affected the entire QGIS process.
- Use `NaN` instead of `0.0` for nodata replacement in `ElevationGrid` to distinguish nodata from sea level.
- Remove legacy `sys.path` manipulation from `nowires.py` and `coverage_engine.py`.
- Fix import ordering violations and remove unused imports across multiple files.
- Normalize copyright headers to consistent `(C) 2026 by Bortre Tenamo`.
- Extract magic numbers into named constants for clarity.
- Remove redundant `sys.path` insertions from test files.
- Prepare repository for public GitHub upload.
- Split coverage helpers into `coverage_compute.py` and `coverage_colors.py`.
- Add a synthetic coverage runtime benchmark under `benchmarks/coverage_runtime.py`.
- Add a live `Coverage Opacity` plugin action for the latest coverage layer.
- Restore tracked 3D scene support for coverage and contour outputs.
- Disable plugin-launched 3D canvas creation on Windows and defer to the native QGIS 3D view workflow there.
- Add CSV, JSON, and HTML report export for P2P and coverage workflows.
- Add TX/RX marker output for point-to-point analysis.
- Add reliability outputs and availability estimates for P2P and coverage reports.
- Improve the Windows 3D fallback guidance for opening the native QGIS 3D view.
- Fix coverage raster cell-center alignment so the heatmap matches the requested map extent.
- Fix DEM north-up sampling so coverage and terrain-derived outputs are not mirrored upside down.
- Fix Windows access violation crash caused by `QgsProject.instance().addMapLayer()` called from inside `processAlgorithm`.
- Fix "layer not correctly generated" error by replacing `RasterDestination`/`VectorDestination` output parameters with `FileDestination` to prevent double-loading conflict with manually queued styled layers.
- Fix DEM raster layers loading on top of coverage/contour outputs; `postProcessAlgorithm` now moves DEM layers to the bottom of the layer tree.
- Fix missing `ANTENNA_AZ` class constant that caused `AttributeError` at algorithm initialization.

## [1.1.0]

- Replace separate area coverage and radius sweep workflows with unified `Coverage Analysis`.
- Add raster-derived coverage range statistics.
- Improve coverage raster styling and controls.
- Add regression coverage for Processing contracts and coverage behavior.
