# AGENTS.md

SPDX-License-Identifier: GPL-3.0-or-later

## CI Pipeline

Six GitHub Actions workflows guard the project:

| Workflow | Triggers | Jobs |
|----------|----------|------|
| `tests.yml` | push, PR | ruff lint, pip-audit, mypy type-check, pytest (Python 3.12, cov ≥64%) |
| `integration.yml` | push, PR, workflow_dispatch | QGIS 4.0 Docker integration tests (digest-pinned) with coverage |
| `benchmark.yml` | push, PR, workflow_dispatch | Benchmark smoke tests (15 min timeout) |
| `codeql.yml` | push/PR to main, weekly cron | CodeQL Python static analysis |
| `version-check.yml` | PR to main | Fails if metadata.txt version not bumped or CHANGELOG.md empty |
| `release.yml` | push of `v*.*.*` tag, workflow_dispatch | Verifies tag matches metadata.txt, builds the `NoWires-X.Y.Z.zip` plugin bundle, extracts the matching CHANGELOG section, and publishes a GitHub Release |

Tool versions are pinned in `constraints-ci.txt`. Each job installs only what it needs via role-specific files (`requirements-lint.txt`, `requirements-typecheck.txt`, `requirements-test.txt`) using `pip install -c constraints-ci.txt -r requirements-<role>.txt`. The single coverage threshold lives in `pyproject.toml` (`[tool.coverage.report] fail_under`); CI invokes `pytest --cov` without a CLI override so the project file is the source of truth.

The unit-test job in `tests.yml` excludes `qgis_integration` and `gdal_integration` markers. Tests that call `band.WriteArray()` / `band.ReadAsArray()` require numpy-2-compatible GDAL bindings and must carry `@pytest.mark.gdal_integration`; they run in the QGIS Docker container via `integration.yml`. Tests that need a full QGIS runtime carry `@pytest.mark.qgis_integration`.

All third-party actions are SHA-pinned. Dependabot manages bumps for both `pip` and `github-actions` ecosystems (see `.github/dependabot.yml`).

All tests must pass locally before committing. See CONTRIBUTING.md for commands.

## Regression Test Naming Convention

Bug-fix regression tests follow the pattern `test_<topic>_<specific_issue>.py`,
named after the module and defect rather than the version. Examples:

- `test_cleanup_stale_shm_scoping.py` — `/dev/shm` cleanup scoping by PID/UID
- `test_contour_pipeline_proxy_auth.py` — proxy auth realm/scheme fix
- `test_batch_writer_csv_injection.py` — CSV formula-injection guard
- `test_haversine_clip.py` — haversine numerical stability clip
- `test_elevation_runtime_error.py` — `assert` → `RuntimeError` in ElevationGrid
- `test_pool_atexit_gating.py` — atexit re-registration accumulation
- `test_executor_partial_counters.py` — partial MP counter preservation on fallback
- `test_contour_pipeline_clip_leak.py` — GDAL dataset leak in clip verification
- `test_pattern_preview_dialog_leak.py` — antenna-preview dialog lifecycle
- `test_hillshade_flush_cache.py` — hillshade pyramid FlushCache before release
- `test_contour_tempdir_cleanup.py` — fallback temp-dir cleanup registration
- `test_shared_dem_atexit_weakref.py` — atexit weak-reference registry for SharedDEMGrid
- `test_batch_owns_clutter_grid.py` — batch clutter-grid ownership flag
- `test_geo_bounds_lat_clamp.py` — latitude clamping + METERS_PER_DEGREE_LAT import
- `test_elevation_zero_div_guard.py` — zero-rows/cols RuntimeError in ElevationGrid
- `test_coverage_summary_zero_div_guard.py` — empty-grid zero-division guard
- `test_coverage_pct_param_defaults.py` — separate default constants for pct params

Do **not** prefix test filenames with version numbers (e.g., `test_v157_…`).

## Source File Size Constraint

All Python source files in this project must strictly adhere to a maximum of **300 lines** per file.

### Rules

- No `.py` file may exceed 300 lines (blank lines and comments are counted toward the limit).
- If a module grows beyond 300 lines, refactor it by extracting responsibilities into new modules.
- Prefer composition and delegation over inheritance — split large classes into focused helper modules.
- Test files (`tests/test_*.py`) are exempt from this limit.
- Bundled third-party code (e.g., `itm/`) is exempt from this limit.

### Enforcement

- Before committing, verify: `find . -name '*.py' ! -path '*/tests/*' ! -path '*/itm/*' ! -path '*/__pycache__/*' -exec wc -l {} + | awk '/total$/ {next} $1 > 300 {print}'` — must return zero files.
- Ruff line-length is set to 99; use it consistently to keep lines compact.

## Changelog Structure

`CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) conventions. It must always have `## [Unreleased]` as the first versioned section (after the header), before any released version sections. Planned or deferred work lives under `### Planned` subsections within `[Unreleased]`. When cutting a release, move completed items from `[Unreleased]` into a new dated `## [X.Y.Z] - YYYY-MM-DD` section that goes immediately after `[Unreleased]`.

## Release Process

This project adheres to [Semantic Versioning](https://semver.org). The version bump reflects the most significant change in the release: MAJOR for breaking API changes, MINOR for new backwards-compatible functionality, PATCH for backwards-compatible bug fixes and zero-behavior-change refactors. A single release may include changes across multiple categories (e.g., PATCH-level cleanups bundled with MINOR-level features) — the bump is determined by the highest-impact change per the classification table below.

### Classification

| Change type                                       | Bump  |
|---------------------------------------------------|-------|
| Bug fix (security, leak, correctness, robustness) | PATCH |
| Refactor with zero behavior change                | PATCH |
| New additive functionality                        | MINOR |
| Public API rename, removed symbol, default change | MAJOR |

Refactors that touch the public API surface escalate to MINOR. Before merging an underscore→public rename or signature change, run `grep -r "from NoWires"` outside the plugin tree; any external importer forces a MINOR bump.

### Release shape

Releases are planned in `CHANGELOG.md` `[Unreleased]` subsections and shipped as one or more focused PRs, sequenced by risk. The preferred organization within a release version follows these shapes:

- **Bugfixes** (PATCH): group by category — security → resource leaks → correctness/robustness. Each fix lands with a regression test that fails without the patch (TDD convention since v1.5.0).
- **Cleanups** (PATCH): group by theme — constants, dedup, decomposition, polish. Golden-file tests (`tests/test_report_export_golden.py`) must produce byte-identical output; zero behavior change is verified, not asserted. Small, tightly-scoped cleanups may be included in a feature-bearing MINOR release.
- **Features** (MINOR or MAJOR): one PR per feature. Scope via brainstorm before code; manual QGIS UI test before tagging (CI cannot validate Qt widgets).

### Pre-flight greps

- **Leak / ownership fixes**: grep `owns_`, `\.close()`, `atexit.register` across the codebase. Prior releases (v1.5.0 → v1.5.1 → v1.5.7) missed sibling sites twice — do one comprehensive pass per leak class.
- **Constant centralization**: grep the magic literal tree-wide; bundle all call sites in one PR so the constant lands with its callers.
- **Public API change**: grep `from NoWires` outside the plugin tree.

### Release gates

- All PRs in the release merged in sequence
- `tests.yml`, `integration.yml`, `benchmark.yml` green on the release commit
- `version-check.yml` passes (metadata.txt bumped; `[Unreleased]` non-empty)
- CHANGELOG entries moved from `[Unreleased]` → `## [X.Y.Z] - YYYY-MM-DD`
- Tag `vX.Y.Z` (triggers `release.yml`)
- Features: manual QGIS UI test recorded in the PR description

## Prohibited Automation

**Never commit, merge, push, or create PRs without explicit user instruction.** These actions modify the repository's public history and must always be user-initiated:

- `git commit` — only when the user explicitly asks to commit
- `git push` — only when the user explicitly asks to push
- `git merge` / PR merge — only when the user explicitly asks to merge
- `gh pr create` — only when the user explicitly asks to create a PR
- `git tag` — only when the user explicitly asks to tag a release

The agent may prepare diffs, run tests, lint, typecheck, and suggest next steps — but must never execute any of the above commands unless the user gives a clear, direct instruction to do so.