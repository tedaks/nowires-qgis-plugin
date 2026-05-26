# Roadmap

SPDX-License-Identifier: GPL-3.0-or-later

Planned work not yet implemented. Items move to [CHANGELOG.md](CHANGELOG.md) once landed.

## Planned for v1.6.7+

### Test harness improvements (runner repository)

These items live in the test-runner repository, not the plugin.

#### Test harness: no expects-error mechanism

`comprehensive-tests-v4.py:849-857` — any exception raised by an algorithm is
classified as FAIL. There is no allow-list for tests that intentionally exercise
guard rails.

**Proposed fix.** Add an optional `"expects_error"` key on test definitions
(string substring to match against the exception message).

#### Test harness: noisy / duplicated warning thresholds

Two issues in `comprehensive-tests-v4.py` analyzers:
1. Same-freq comparison warns "panels are identical" even when `same_freq=True`.
2. `itm < fspl` and `excess < 0` both fire for the same condition.

#### Test harness: mislabeled tests

Two test definitions have descriptions contradicting their parameters:
1. `pct_time10` labeled "conservative" should be "optimistic" (and vice versa).
2. `cov_polar_h_manila` sets `polarization: 1` (Vertical) but says "horizontal".

### No compiled API reference documentation (LOW)

The project has excellent docstrings but no compiled API reference (Sphinx or
similar). The `docs/` directory is in `.gitignore`.

**Proposed fix.** Add a `docs/` directory with a Sphinx `conf.py` and
auto-generate API references from docstrings. Wire into CI as a
`docs` job that fails on broken references.

**Status:** ⏳ Deferred — not included in v1.6.6.
