# NoWires QGIS Plugin — Consolidated Code Review

Repository: https://github.com/tedaks/nowires-qgis-plugin  
Reviewed: 2026-05-09  
Revised: 2026-05-09

---

# Executive Summary

The repository shows strong domain knowledge and a reasonably mature architecture for RF propagation analysis inside QGIS. The project includes:

- Modular separation of propagation, raster, antenna, clutter, and reporting logic
- Defensive downloader/cache handling
- Significant unit-test coverage plus QGIS 4 runtime integration tests (89 tests)
- GitHub Actions workflows (lint, unit tests, QGIS 4 integration, benchmarks)
- Practical multiprocessing safeguards

Overall assessment:

| Area | Status |
|---|---|
| Core architecture | Good |
| RF/terrain logic structure | Good |
| Test breadth | Good |
| Packaging consistency | Fixed — `pyproject.toml` coverage source now points to `NoWires` |
| QGIS runtime confidence | Good — QGIS 4 Docker CI with 89 integration tests |
| Release readiness | Nearly ready |

---

# Resolved Issues

## 1. Duplicated Logic in `coverage_compute.py` — FIXED

### Original Finding
Two nearly identical branches computed `clutter_total_db`, `total_path_loss_db`, and `prx` — one for capped losses (with debug log), one for normal.

### Fix
Collapsed into a single computation block. The capped case still logs at debug level, but the return dict is computed once.

---

## 2. Coverage Configuration Mismatch — FIXED

### Original Finding
`pyproject.toml` had `source = ["nowires_qgis_plugin"]` but the actual import package is `NoWires`.

### Fix
Changed to `source = ["NoWires"]` in `pyproject.toml`.

---

## 3. QGIS Runtime Validation in CI — RESOLVED (pre-existing)

The project now has `.github/workflows/integration.yml` using `qgis/qgis:4.0` with 89 `qgis_integration`-marked tests covering:
- Algorithm parameter registration and output definitions
- Vector layer loading (P2P, batch markers)
- Raster style roundtrip (coverage palette, delta style)
- Contour and P2P symbology on real layers
- Processing utils layer loading
- QgsProject state persistence
- Coordinate transforms
- DEM geometry operations
- DEM elevation properties on raster layers
- 3D terrain configuration APIs
- Auth config parameter handling

---

## 4. Metadata Formatting — NOT AN ISSUE

The review claimed `metadata.txt` was compressed/minified. In fact, `metadata.txt` uses standard INI format with normal line breaks and multiline `about=` / `changelog=` fields. No change needed.

---

## 5. Provider Import Resilience — FIXED

### Original Finding
`provider.py` used bare `from .XXX import YYY` for all 5 algorithms in `loadAlgorithms()`. One failing dependency would prevent the entire provider from loading.

### Fix
Changed to a table-driven approach with per-algorithm `try/except`. If one algorithm fails to import, the others still load. Failures are logged with full traceback via `logger.exception()`.

---

## 6. README `coverage_colors.py` Reference — NOT AN ISSUE

The review claimed README referenced `coverage_colors.py`. No such reference exists. README correctly lists `coverage_palette.py`.

---

## 7. Versioning Consistency — NOT AN ISSUE

The review claimed version mismatch between README (1.4.0) and metadata. Current state:
- `pyproject.toml`: 1.5.0
- `metadata.txt`: version=1.5.0
- `README.md`: "version 1.5.0"
- All consistent. The 1.4.0 reference in `metadata.txt` is a historical changelog entry.

---

# Positive Findings

## Strong Modularization

The repo cleanly separates propagation, raster operations, contour generation, DEM handling, reporting, antenna logic, and multiprocessing.

## Defensive Downloader Design

`tile_download_base.py` includes redirect validation, atomic replace, content-length checks, tile validation, retry handling, and cache validation.

## Comprehensive QGIS 4 Integration Tests

89 integration tests run in a `qgis/qgis:4.0` Docker container, covering parameter registration, vector/raster layer lifecycle, symbology, coordinate transforms, project state, and 3D APIs.

---

# Final Verdict

The project is technically sound and well-structured. The identified issues have been resolved or confirmed as non-issues. With the current CI pipeline (lint + unit tests + QGIS 4 integration + benchmarks), the plugin is release-ready.