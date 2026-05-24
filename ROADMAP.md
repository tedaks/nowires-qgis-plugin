# Roadmap

SPDX-License-Identifier: GPL-3.0-or-later

Planned work not yet implemented. Items move to [CHANGELOG.md](CHANGELOG.md) once landed.

## v1.6.3 — released 2026-05-24

All planned items landed. See [CHANGELOG.md](CHANGELOG.md#163---2026-05-24) for details.

## v1.6.4 — coverage push ✅

Target: 85% combined unit + integration test coverage.
**Achieved: 85%** (unit + GDAL + QGIS integration via Docker QGIS 4.0 + matplotlib).

Key improvements:
- `algorithm/coverage_comparison.py`: 26% → 91%
- `algorithm/p2p.py`: 33% → 99%
- `comparison/outputs.py`: 25% → 95%
- `radio_coverage/legend.py`: 24% → 74%
- `contour/smoothing.py`: 75% → 86%
- `p2p/compute.py`: 95% → 97%

- ~~Increase `fail_under` coverage threshold~~ ✅ 59% → 65%
- ~~106 unit tests for core modules~~ ✅ done
- ~~12 non-Qt GUI helper tests~~ ✅ done
- ~~21 Docker QGIS + algorithm execution tests~~ ✅ done
- ~~7 comparison outputs + 4 contour module tests~~ ✅ done
- ~~12 Qt widget tests with matplotlib~~ ✅ done
- Remaining uncovered (~990 lines): Qt GUI lifecycle (nowires.py, p2p/chart.py, three_d.py), GDAL pipelines (contour.py, pipeline.py) — these require either QMainWindow infrastructure or real Copernicus DEM downloads
