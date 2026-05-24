# Roadmap

SPDX-License-Identifier: GPL-3.0-or-later

Planned work not yet implemented. Items move to [CHANGELOG.md](CHANGELOG.md) once landed.

## v1.6.3 — released 2026-05-24

All planned items landed. See [CHANGELOG.md](CHANGELOG.md#163---2026-05-24) for details.

## v1.6.4 — coverage push

Target: 85% combined unit + integration test coverage.
Progress: **83% combined** (unit + GDAL + QGIS integration via Docker QGIS 4.0).

Key module improvements:
- `algorithm/coverage_comparison.py`: 26% → 91%
- `algorithm/p2p.py`: 33% → 99%
- `comparison/outputs.py`: 25% → 95%
- `contour/smoothing.py`: 75% → 86%
- `p2p/compute.py`: 95% → 97%

- ~~Increase `fail_under` coverage threshold~~ ✅ 59% → 65%
- ~~106 unit tests for core modules~~ ✅ done
- ~~12 non-Qt GUI helper tests~~ ✅ done
- ~~21 Docker QGIS integration tests~~ ✅ done (algorithm execution + comparison outputs + contour modules)
- Remaining 2% gap (~104 lines): `algorithm/contour.py` full pipeline, `contour/pipeline.py` tile download, `nowires.py` GUI lifecycle, `p2p/chart.py` chart rendering — all require either complex GDAL tile download setup or Qt widget infrastructure
