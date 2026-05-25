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

## v1.6.5 — review-driven hardening (planned)

Findings from a manual code review (2026-05-24). Each item below was verified by reading
the source — speculative findings from the same review pass are not listed.

Bump classification: PATCH (correctness + robustness, zero public-API change). Each
item lands with a regression test that fails without the patch, per TDD convention
since v1.5.0.

### SAALOS scalar / vector numerical asymmetry

The vectorised SAALOS path in `clutter/_saalos_vec.py` defensively clamps three
quantities that the scalar path in `clutter/saalos.py` does not. At edge inputs the
two implementations diverge — scalar returns ±inf or NaN where vector returns a
finite loss. Coverage maps (which always use the vector path) and P2P analyses
(which use the scalar path for single-link compute) will therefore disagree on
the same input.

| Site | Scalar (unsafe) | Vector (safe) |
|---|---|---|
| `saalos.py:79` | `crpc = dp - 1.0 / dp` | `_saalos_vec.py:44` clamps `dp` to ≥ 1.0 in the denominator |
| `saalos.py:109` | `math.log10(tsp)` | `_saalos_vec.py:80` clamps `tsp` to ≥ 1e-30 |
| `saalos.py:118` | `math.log10(rsp)` | `_saalos_vec.py:94` clamps `rsp` to ≥ 1e-30 |

**Trigger inputs.** After the 5-iteration refraction loop, `dp` shrinks toward zero
at grazing incidence (line 82: `dp = pd - d1a`). `tsp = 1 - rsp` reaches zero when
the reflection coefficient `q → ±1` (lines 92–104). `rsp = q²` reaches zero when
`q → 0`, i.e. when `cttc ≈ ctic` at the matched-angle case.

**Proposed fix.** Mirror the vector clamps into the scalar path so both
implementations are bit-for-bit equivalent on the safe range and finite on the
edge range:

```python
# saalos.py:79
crpc = dp - 1.0 / max(dp, 1.0)

# saalos.py:109
arte = 0.0195 * crpc - 20.0 * math.log10(max(tsp, 1e-30))

# saalos.py:118
arte = d1a * q - (18.0 * math.log10(max(rsp, 1e-30))) / math.exp(hone / 37.5)
```

**Regression test.** `tests/test_saalos_scalar_vector_parity.py` —
property-based test (hypothesis) drawing `(d_m, cch_m, h_tx_m, h_rx_m,
h_rx_gnd_m, pol, f_mhz)` from the documented input domain plus boundary cases
(`dp → 0`, `q → ±1`, `q → 0`). For each input, assert
`clutter_loss_saalos(...) == clutter_loss_saalos_vec(...)` within 1e-9, and assert
both are finite. Currently fails on the boundary draws.

### Tile download redirect scheme check

`tile_download_base.py:101` compares only `urlsplit(final_url).netloc` against
`base_url`, not the scheme. A redirect from `https://copernicus-dem-30m.s3...` to
`http://copernicus-dem-30m.s3...` passes the check and downloads the tile over
plaintext. With a hostile network operator (or a poisoned resolver) this enables
a downgrade attack: the cert pinning is effectively skipped on the second hop.

**Proposed fix.**

```python
if base_url is not None:
    base = urlsplit(base_url)
    final = urlsplit(final_url)
    if (final.netloc.lower() != base.netloc.lower()
            or final.scheme != base.scheme):
        raise RuntimeError("Unexpected redirect to: " + final_url)
```

**Regression test.** `tests/test_tile_download_redirect_scheme.py` — install a
mock opener that 302-redirects `https://host/x.tif` to `http://host/x.tif` and
assert `download_tile_with_retry(...)` returns `None` (or raises) without reading
the body.

### Retry backoff lacks jitter

`tile_download_base.py:140, 153, 177, 198` all sleep `2 ** attempt` seconds with
no jitter. When multiple QGIS workers (`NOWIRES_MAX_WORKERS` defaults up to 16)
each retry the same tile after a 503 or transient timeout, they retry in
lockstep — the second wave is more likely to provoke the same throttling, then
the third wave, etc. (thundering herd).

**Proposed fix.** Move backoff to a helper:

```python
# tile_download_base.py (module scope)
import random

def _backoff_seconds(attempt: int) -> float:
    return 2 ** attempt + random.uniform(0, 1)
```

…and replace every `time.sleep(2 ** attempt)` and `wait_secs = 2 ** attempt`
with `_backoff_seconds(attempt)`. The `Retry-After` branch keeps its
header-supplied value unchanged.

**Regression test.** `tests/test_tile_download_backoff_jitter.py` — seed
`random` deterministically, call `_backoff_seconds(attempt)` for attempts 0–3,
assert each result is in `[2**attempt, 2**attempt + 1)` and that two
consecutive calls with different seeds differ.

### URL logged unsanitised to QGIS feedback

`tile_download_base.py:83` calls `feedback.pushInfo("Downloading: " + tile_url)`.
Today's `tile_url` is built from a hard-coded base + tile name + extension, so
no query string can be appended — but the base URL is a constructor argument
and a future caller passing a presigned S3 URL would leak the signature into
the QGIS message log.

**Proposed fix.** Strip the query string for the user-facing log; keep the full
URL in the structured `logger.debug` call.

```python
from urllib.parse import urlsplit, urlunsplit

def _redact_query(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(parts._replace(query="", fragment=""))

if feedback:
    feedback.pushInfo("Downloading: " + _redact_query(tile_url))
logger.debug("Downloading full URL: %s", tile_url)
```

**Regression test.** `tests/test_tile_download_url_redaction.py` — pass a URL
with a `?X-Amz-Signature=...` query, capture pushInfo, assert the signature is
not in the captured string.

### Silent exception suppression in shared-memory finalizer

`radio_coverage/pool.py:129-130, 143-144` swallow every exception from
`SharedMemory.close()` / `.unlink()` with `except Exception: pass`. Real
failures (permission errors, double-unlink, missing segment) are invisible.
Past `/dev/shm` cleanup bugs (`test_cleanup_stale_shm_scoping`) were exactly
this class.

**Proposed fix.**

```python
def _final_cov_pool():
    with _cov_lock:
        global _cov_shm, _cov_grid_data
        if _cov_grid_data is not None:
            _cov_grid_data = None
        if _cov_shm is not None:
            try:
                _cov_shm.close()
                _cov_shm.unlink()
            except FileNotFoundError:
                pass  # already unlinked — normal on second run
            except OSError as exc:
                logger.debug("shm finalizer: %s", exc)
            _cov_shm = None
```

Apply the same narrowing to the close-only branch at line 142.

**Regression test.** `tests/test_pool_finalizer_logs_errors.py` — monkeypatch
`SharedMemory.unlink` to raise `PermissionError`, call `_final_cov_pool()` under
`caplog`, assert the message is logged at DEBUG and that the function does not
raise.

### Sanitiser whitespace coverage

`sanitizers.py:6` defines `_UNICODE_WHITESPACE = "\t\r　  ﻿"`
— ASCII space ` ` is intentionally **not** in the set, so `" =cmd"` with a
leading regular space bypasses the formula-injection guard. Excel auto-trims
leading whitespace when rendering cells, so this is exploitable against an
Excel consumer of the CSV.

**Decision required.** Two options:
1. Add `" "` to `_UNICODE_WHITESPACE`. Risk: trims legitimate leading spaces in
   user-supplied free-text fields (point notes, custom IDs). Existing
   `test_batch_writer_csv_injection.py` does not cover this case.
2. Keep stripping conservative and instead match the formula-trigger check
   against the **first non-whitespace character** rather than `s[0]`. Preserves
   the original string verbatim while still catching `" =cmd"`.

Preferred: option 2 (preserves user content). Implementation sketch:

```python
def csv_safe(value):
    s = str(value).replace("\r", " ").replace("\n", " ")
    stripped = s.lstrip(_UNICODE_WHITESPACE + " ")
    if stripped and stripped[0] in _FORMULA_TRIGGER_CHARS:
        return "'" + s
    if stripped.startswith("-") and len(stripped) > 1:
        try:
            float(stripped)
        except ValueError:
            return "'" + s
    return s
```

**Regression test.** Extend `test_batch_writer_csv_injection.py` with
`(" =SUM(A1)", "'  =SUM(A1)")` and similar cases for `+`, `@`, U+2212.

### Release shape

Group by category per `AGENTS.md`:
- Security: redirect scheme check, URL redaction, sanitiser whitespace
- Correctness: SAALOS scalar/vector parity
- Robustness: backoff jitter, shm finalizer logging

One PR per category. Manual QGIS UI test not required (no Qt-widget changes).
