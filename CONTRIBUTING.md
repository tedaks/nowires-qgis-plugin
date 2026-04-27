# Contributing

## Development Notes

- Target platform: QGIS 4.x
- Qt target: Qt 6 / PyQt 6 only; do not add Qt 5 compatibility shims
- Language: Python
- Raster/terrain source: Copernicus GLO-30
- Propagation engine: bundled `itm/`

## Local Checks

Run the repository test suite before opening a pull request:

```bash
pytest -q
```

## Manual Testing

For UI and Processing integration checks, copy the `NoWires` folder into your QGIS plugins directory and test inside QGIS.

## Pull Requests

- Keep changes focused.
- Update user-facing docs when behavior changes.
- Preserve third-party attribution in `NOTICE.md`.
- Avoid committing generated caches or temporary analysis outputs.
