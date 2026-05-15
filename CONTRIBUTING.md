# Contributing

SPDX-License-Identifier: GPL-3.0-or-later

Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>

## Development Notes

- Target platform: QGIS 4.x
- Qt target: Qt 6 / PyQt 6 only; do not add Qt 5 compatibility shims
- Language: Python
- Raster/terrain source: Copernicus GLO-30
- Propagation engine: bundled `itm/`

## Source File Size Constraint

All Python source files in this project must strictly adhere to a maximum of **300 lines** per file.

- No `.py` file (excluding `tests/` and `itm/`) may exceed 300 lines (including blank lines and comments).
- If a module grows beyond 300 lines, refactor it by extracting responsibilities into new modules.
- Prefer composition and delegation over inheritance — split large classes into focused helper modules.
- Ruff line-length is set to 99; use it consistently to keep lines compact.
- Before committing, verify: `find . -name '*.py' ! -path '*/tests/*' ! -path '*/itm/*' ! -path '*/__pycache__/*' -exec wc -l {} + | awk '$1 > 300'` — must return zero files.

## CI Pipeline

The project uses three GitHub Actions workflows run on every push and pull request:

### tests.yml — Lint, Type-Check, Audit, Unit Tests

| Job | Description |
|-----|-------------|
| `lint` | Runs `ruff check .` and enforces the 300-line file limit |
| `audit` | Installs the project + dev extras and runs `pip-audit --requirement requirements-ci.txt` |
| `mypy` | Runs `mypy . --config-file mypy.ini` for static type checking |
| `pytest` | Runs `pytest -m "not benchmark and not qgis_integration" --cov` on Python 3.12. Coverage threshold lives in `pyproject.toml` (currently 59%). |

Tool versions are pinned in `constraints-ci.txt`. Each job installs only its role's deps via `requirements-{lint,typecheck,test}.txt` using `pip install -c constraints-ci.txt -r requirements-<role>.txt`.

### integration.yml — QGIS Integration Tests (Docker)

Runs inside the `qgis/qgis:4.0` container on every push/PR. Runs the QGIS integration suite, GDAL compatibility tests, and raster I/O integration tests, all sharing one combined coverage file. Blocking — failures prevent merge.

### benchmark.yml — Benchmark Smoke Tests

Runs `pytest -m benchmark` with a 15-minute timeout on every push/PR (and `workflow_dispatch`).

### version-check.yml — Version and Changelog Gate

Runs on PRs to `main`. Fails if `metadata.txt` version was not bumped or `CHANGELOG.md` `[Unreleased]` section has no entries.

## Local Checks

Run the repository test suite before opening a pull request:

```bash
# Lint
ruff check .

# Type check
mypy . --config-file mypy.ini

# Unit and contract tests with coverage (threshold from pyproject.toml)
pytest -q -m "not benchmark and not qgis_integration" --cov

# File-size enforcement
find . -name '*.py' ! -path '*/tests/*' ! -path '*/itm/*' ! -path '*/__pycache__/*' -exec wc -l {} + | awk '/total$/ {next} $1 > 300 {print}'
```

## Integration Testing (Docker)

```bash
docker run --rm \
  -v $(pwd):/plugin -w /plugin \
  -e QGIS_PREFIX_PATH=/usr -e QT_QPA_PLATFORM=offscreen \
  qgis/qgis:4.0 \
  bash -c 'pip install --break-system-packages pytest pytest-cov numpy defusedxml hypothesis && pytest -m qgis_integration -v'
```

## Manual Testing

For UI and Processing integration checks, copy the `NoWires` folder into your QGIS plugins directory and test inside QGIS.

## Pull Requests

- Keep changes focused.
- Update user-facing docs when behavior changes.
- Bump `metadata.txt` version and add entries to `CHANGELOG.md` `[Unreleased]`.
- Preserve third-party attribution in `NOTICE.md`.
- Avoid committing generated caches or temporary analysis outputs.
- Do not add comments unless they explain non-obvious logic.