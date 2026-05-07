# Contributing

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
- Before committing, verify: `find . -name '*.py' ! -path '*/tests/*' ! -path '*/itm/*' -exec wc -l {} + | awk '$1 > 300'` — must return zero files.

## Local Checks

Run the repository test suite before opening a pull request:

```bash
pytest -q
```

Optionally run the linter:

```bash
ruff check .
```

Optionally check for file-size violations:

```bash
find . -name '*.py' ! -path '*/tests/*' ! -path '*/itm/*' -exec wc -l {} + | awk '$1 > 300'
```

## Manual Testing

For UI and Processing integration checks, copy the `NoWires` folder into your QGIS plugins directory and test inside QGIS.

## Pull Requests

- Keep changes focused.
- Update user-facing docs when behavior changes.
- Preserve third-party attribution in `NOTICE.md` and `THIRD_PARTY_NOTICES.md`.
- Avoid committing generated caches or temporary analysis outputs.
- Do not add comments unless they explain non-obvious logic.