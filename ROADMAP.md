# Roadmap

SPDX-License-Identifier: GPL-3.0-or-later

Planned work not yet implemented. Items move to [CHANGELOG.md](CHANGELOG.md) once landed.

## v1.6.3 — released 2026-05-24

All planned items landed. See [CHANGELOG.md](CHANGELOG.md#163---2026-05-24) for details.

## v1.6.4 — coverage push

Target: 85% combined unit + integration test coverage.
Progress: **80% combined** (unit + GDAL + QGIS integration via Docker QGIS 4.0).

- ~~Increase `fail_under` coverage threshold from 59% to 65%~~ ✅ done
- ~~Add unit tests for `elevation.py`, `tile_download_base.py`, `nowires.py`, `batch/outputs.py`, `batch/writer.py`, `radio_coverage/pool.py`, `contour/smoothing.py`~~ ✅ 106 tests added
- ~~Add unit tests for non-Qt paths in `three_d.py`, `report/markers.py`, `p2p/chart_format.py`~~ ✅ 12 tests added
- ~~Add starter Docker QGIS integration tests~~ ✅ 9 tests added (`test_qgis_integration_extended.py`)
- Expand Docker QGIS integration tests for full algorithm orchestration: `algorithm/batch.py`, `algorithm/coverage_comparison.py`, `algorithm/contour.py`, `algorithm/coverage.py`, `comparison/outputs.py` (remaining ~5% gap to 85%)
- Add unit tests for `radio_coverage/legend.py` legend data builders (Qt-dependent)
