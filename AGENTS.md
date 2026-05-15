# AGENTS.md

SPDX-License-Identifier: GPL-3.0-or-later

## CI Pipeline

Six GitHub Actions workflows guard the project:

| Workflow | Triggers | Jobs |
|----------|----------|------|
| `tests.yml` | push, PR | ruff lint, pip-audit, mypy type-check, pytest (Python 3.12, cov ≥59%) |
| `integration.yml` | push, PR, workflow_dispatch | QGIS 4.0 Docker integration tests (digest-pinned) with coverage |
| `benchmark.yml` | push, PR, workflow_dispatch | Benchmark smoke tests (15 min timeout) |
| `codeql.yml` | push/PR to main, weekly cron | CodeQL Python static analysis |
| `version-check.yml` | PR to main | Fails if metadata.txt version not bumped or CHANGELOG.md empty |
| `release.yml` | push of `v*.*.*` tag, workflow_dispatch | Verifies tag matches metadata.txt, builds the `NoWires-X.Y.Z.zip` plugin bundle, extracts the matching CHANGELOG section, and publishes a GitHub Release |

Tool versions are pinned in `constraints-ci.txt`. Each job installs only what it needs via role-specific files (`requirements-lint.txt`, `requirements-typecheck.txt`, `requirements-test.txt`) using `pip install -c constraints-ci.txt -r requirements-<role>.txt`. The single coverage threshold lives in `pyproject.toml` (`[tool.coverage.report] fail_under`); CI invokes `pytest --cov` without a CLI override so the project file is the source of truth.

All third-party actions are SHA-pinned. Dependabot manages bumps for both `pip` and `github-actions` ecosystems (see `.github/dependabot.yml`).

All tests must pass locally before committing. See CONTRIBUTING.md for commands.

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