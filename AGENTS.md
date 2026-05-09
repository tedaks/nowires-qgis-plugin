# AGENTS.md

SPDX-License-Identifier: GPL-3.0-or-later

## Source File Size Constraint

All Python source files in this project must strictly adhere to a maximum of **300 lines** per file.

### Rules

- No `.py` file may exceed 300 lines (excluding blank lines and comments are still counted).
- If a module grows beyond 300 lines, refactor it by extracting responsibilities into new modules.
- Prefer composition and delegation over inheritance — split large classes into focused helper modules.
- Test files (`tests/test_*.py`) are exempt from this limit.
- Bundled third-party code (e.g., `itm/`) is exempt from this limit.

### Enforcement

- Before committing, verify: `find . -name '*.py' ! -path '*/tests/*' ! -path '*/itm/*' -exec wc -l {} + | awk '$1 > 300'` — must return zero files.
- Ruff line-length is set to 99; use it consistently to keep lines compact.