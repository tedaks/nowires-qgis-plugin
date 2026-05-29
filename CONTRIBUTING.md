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

- No `.py` file (excluding `tests/`, `itm/`, and `benchmarks/`) may exceed 300 lines (including blank lines and comments).
- If a module grows beyond 300 lines, refactor it by extracting responsibilities into new modules.
- Prefer composition and delegation over inheritance — split large classes into focused helper modules.
- Ruff line-length is set to 99; use it consistently to keep lines compact.
- Before committing, verify: `find . -name '*.py' ! -path '*/tests/*' ! -path '*/itm/*' ! -path '*/benchmarks/*' ! -path '*/__pycache__/*' -exec wc -l {} + | awk '/total$/ {next} $1 > 300 {print}'` — must return zero files.

## CI Pipeline

The project uses six GitHub Actions workflows run on every push and pull request:

### tests.yml — Lint, Type-Check, Audit, Unit Tests

| Job | Description |
|-----|-------------|
| `lint` | Runs `ruff check .` and enforces the 300-line file limit |
| `audit` | Runs `pip-audit --requirement constraints-ci.txt` against the pinned dependency list, then audits the full dependency tree |
| `mypy` | Runs `mypy . --config-file mypy.ini` for static type checking |
| `import-linter` | Runs `lint-imports` to check import architecture rules |
| `pytest` | Runs `pytest -m "not benchmark and not qgis_integration and not gdal_integration" --cov` on Python 3.12. Coverage threshold lives in `pyproject.toml` (currently 64%). Isolation-sensitive tests run separately. |

### integration.yml — QGIS Integration Tests (Docker)

Runs inside the `qgis/qgis:4.0` container on every push/PR. Runs the QGIS integration suite, GDAL compatibility tests, and raster I/O integration tests, all sharing one combined coverage file. Coverage is informational (`--cov-fail-under=0`); the unit-test job enforces the project threshold. Blocking — failures prevent merge.

### benchmark.yml — Benchmark Smoke Tests

Runs `pytest -m benchmark` with a 15-minute timeout on every push/PR (and `workflow_dispatch`).

### codeql.yml — CodeQL Static Analysis

Runs on push/PR to `main` and weekly cron. Performs Python static analysis via CodeQL.

### version-check.yml — Version and Changelog Gate

Runs on PRs and pushes to `main`. For PRs, skips enforcement for Dependabot PRs, PRs labelled `no-version-bump` or `release`, and docs-only diffs (explicit allowlist: `docs/*`, `README.md`, `NOTICE.md`, `ROADMAP.md`, `AGENTS.md`, `CONTRIBUTING.md`, `USERS-GUIDE.md`, `Technical_Documentation.md`). Always checks that all six version-bearing locations (metadata.txt, metadata.txt changelog, CHANGELOG.md, pyproject.toml `version`, pyproject.toml `current_version`, README.md) are aligned. Fails if metadata.txt version has not been bumped from the base branch.

## Local Checks

Run the repository test suite before opening a pull request:

```bash
# Lint
ruff check .

# Type check
mypy . --config-file mypy.ini

# Unit and contract tests with coverage (threshold from pyproject.toml)
PYTHONPATH="$(pwd)" pytest -q -m "not benchmark and not qgis_integration and not gdal_integration" --cov

# File-size enforcement
find . -name '*.py' ! -path '*/tests/*' ! -path '*/itm/*' ! -path '*/benchmarks/*' ! -path '*/__pycache__/*' -exec wc -l {} + | awk '/total$/ {next} $1 > 300 {print}'
```

## Integration Testing (Docker)

```bash
docker run --rm \
  -v $(pwd):/project:ro -w /project \
  -e QGIS_PREFIX_PATH=/usr -e QT_QPA_PLATFORM=offscreen \
  -e PYTHONPATH=/project:/usr/share/qgis/python \
  qgis/qgis:4.0@sha256:6f33d932b56305a550d9e079d64daeabca71fcc97101bba1ca578c55c0e1439b \
  bash -c 'python3 -m venv --system-site-packages /opt/ci-venv && \
    export PATH=/opt/ci-venv/bin:$PATH && \
    pip install -c constraints-ci.txt -r requirements-test.txt && \
    pip check && \
    pytest -m qgis_integration -v --tb=short && \
    pytest tests/test_gdal_compat.py -v --tb=short && \
    pytest tests/test_raster_io_integration.py -v --tb=short && \
    pytest -m gdal_integration -v --tb=short'
```

## Integration Testing (Local macOS QGIS)

The macOS QGIS app bundle has hardened runtime and a non-standard Python
stdlib layout. Four setup steps are required:

1. **Create stdlib symlinks** — the bundled Python 3.12 binary expects its
   stdlib at `$PYTHONHOME/lib/python3.12/`, but QGIS stores it flat under
   `Resources/python3.11/` (the `3.11` directory name is misleading; the
   `.so` files are `cpython-312`). Create a `lib/python3.12` subtree with
   symlinks back to the flat directory:

   ```bash
   QGIS_STDLIB=/Applications/QGIS-final-4_0_2.app/Contents/Resources/python3.11
   mkdir -p "$QGIS_STDLIB/lib/python3.12"
   for item in "$QGIS_STDLIB"/*; do
     name=$(basename "$item")
     [ "$name" = "lib" ] || [ "$name" = "site-packages" ] && continue
     [ -e "$QGIS_STDLIB/lib/python3.12/$name" ] || ln -sf "$item" "$QGIS_STDLIB/lib/python3.12/$name"
   done
   ln -sf "$QGIS_STDLIB/site-packages" "$QGIS_STDLIB/lib/python3.12/site-packages"
   ```

2. **Re-sign python3.12** — add the `disable-library-validation` entitlement so
   pip-installed packages (e.g. pytest) can load alongside QGIS-signed ones:

   ```bash
   codesign -f -s - --entitlements /path/to/entitlement.plist \
     /Applications/QGIS-final-4_0_2.app/Contents/MacOS/python3.12
   ```

   where `entitlement.plist` contains:

   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
     "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
   <plist version="1.0">
   <dict>
     <key>com.apple.security.cs.disable-library-validation</key>
     <true/>
   </dict>
   </plist>
   ```

3. **Restore numpy 1.26.4** — pip may replace it with a newer major version;
   QGIS-bundled packages (shapely, etc.) are compiled against 1.26.4 and struct
   sizes changed between major versions:

   ```bash
   QGIS_PYTHON=/Applications/QGIS-final-4_0_2.app/Contents/MacOS/python3.12
   PYTHONHOME=/Applications/QGIS-final-4_0_2.app/Contents/Resources/python3.11 \
   DYLD_FRAMEWORK_PATH=/Applications/QGIS-final-4_0_2.app/Contents/Frameworks \
   QGIS_PREFIX_PATH=/Applications/QGIS-final-4_0_2.app/Contents/MacOS \
   PROJ_LIB=/Applications/QGIS-final-4_0_2.app/Contents/Resources/qgis/proj \
   PROJ_DATA=/Applications/QGIS-final-4_0_2.app/Contents/Resources/qgis/proj \
   "$QGIS_PYTHON" -m pip install --break-system-packages numpy==1.26.4 pytest-cov
   ```

4. **Run the tests** with PYTHONHOME, DYLD_FRAMEWORK_PATH, and PROJ paths set:

   ```bash
   PYTHONHOME=/Applications/QGIS-final-4_0_2.app/Contents/Resources/python3.11 \
   DYLD_FRAMEWORK_PATH=/Applications/QGIS-final-4_0_2.app/Contents/Frameworks \
   QGIS_PREFIX_PATH=/Applications/QGIS-final-4_0_2.app/Contents/MacOS \
   PROJ_LIB=/Applications/QGIS-final-4_0_2.app/Contents/Resources/qgis/proj \
   PROJ_DATA=/Applications/QGIS-final-4_0_2.app/Contents/Resources/qgis/proj \
   QT_QPA_PLATFORM=offscreen \
   PYTHONPATH=/Applications/QGIS-final-4_0_2.app/Contents/Resources/python3.11/site-packages:$(pwd) \
   /Applications/QGIS-final-4_0_2.app/Contents/MacOS/python3.12 \
     -m pytest -m qgis_integration -v --tb=short && \
   /Applications/QGIS-final-4_0_2.app/Contents/MacOS/python3.12 \
     -m pytest tests/test_gdal_compat.py -v --tb=short && \
   /Applications/QGIS-final-4_0_2.app/Contents/MacOS/python3.12 \
     -m pytest tests/test_raster_io_integration.py -v --tb=short && \
   /Applications/QGIS-final-4_0_2.app/Contents/MacOS/python3.12 \
     -m pytest -m gdal_integration -v --tb=short
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

## Release Process

See the [Release Process](AGENTS.md#release-process) section in `AGENTS.md` for version classification rules, PR sequencing, pre-flight greps, and release gates.