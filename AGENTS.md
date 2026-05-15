# AGENTS.md

SPDX-License-Identifier: GPL-3.0-or-later

## CI Pipeline

Three GitHub Actions workflows run on every push and pull request:

| Workflow | Triggers | Jobs |
|----------|----------|------|
| `tests.yml` | push, PR | ruff lint, pip-audit, mypy type-check, pytest (Python 3.9 + 3.12, cov ≥61%) |
| `integration.yml` | push/PR to main, workflow_dispatch | QGIS 4.0 Docker integration tests with coverage |
| `benchmark.yml` | push/PR to main, workflow_dispatch | Benchmark smoke tests (15 min timeout) |
| `version-check.yml` | PR to main | Fails if metadata.txt version not bumped or CHANGELOG.md empty |

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