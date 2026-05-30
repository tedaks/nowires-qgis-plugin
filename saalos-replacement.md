# Plan: Replace saalos with ITU-R P.833-9 §2.1

## Background

`clutter/saalos.py` and `clutter/_saalos_vec.py` implement the saalos vegetation
clutter-loss algorithm originally written by Sid Shumate for ITWOM 3.0 (copyright
© 2011 Shumate / Givens & Bell, Inc., all rights reserved, commercial use
restricted). The reimplementation intentionally targets bit-for-bit numeric parity
with the ITWOM 3.0 reference C code (`_saalos_vec.py:15–20`), which makes the
independent-expression defence difficult to sustain.

**Goal:** Replace both files with a clean implementation of Am from ITU-R P.833-9
§2.1, remove all saalos test files, clean up the dead context fields and pipeline
code that only existed to support saalos, update attribution in NOTICE.md, and
leave every existing caller working without any change to their public API.

---

## Source document

**ITU-R Recommendation P.833-9 (2016), "Attenuation in vegetation," Annex 1 §2.1,
"Terrestrial path with one terminal in woodland."**

All parameter values, formula text, and quoted statements are taken directly from
this document. Nothing is inferred or extrapolated beyond what the document states.

---

## Model selection: Am as clutter loss

### P.833-9 §2.1 Equation 1

The document gives:

```
Aev = Am · [1 − exp(−d · γ / Am)]     (Eq. 1)
```

where:

| Symbol | Definition (verbatim from document) |
|--------|-------------------------------------|
| `d`    | length of path within woodland (m) |
| `γ`    | specific attenuation for very short vegetative paths (dB/m) |
| `Am`   | maximum attenuation for one terminal within a specific type and depth of vegetation (dB) |

The document defines `d` as the distance from the **woodland boundary** to the
receiver. Figure 1: "the transmitter is outside the woodland and the receiver is a
certain distance, d, within it."

### Why Eq. 1 with a proxied d is not used

`d` (woodland boundary → receiver depth) is not available from the inputs to
`compute_advanced_loss`. The land-cover raster classifies each pixel as vegetation
or not; it does not give distance from the pixel to the nearest forest boundary.
No proxy is derived from or sanctioned by the document.

### Why Am alone is used

P.833-9 §2.1 states directly:

> "It may also be noted that Am is equivalent to the clutter loss often quoted for
> a terminal obstructed by some form of ground cover or clutter."

This is the document's explicit statement that Am is the appropriate value when
modelling a terminal "obstructed by ground cover or clutter." It is the d → ∞
asymptote of Eq. 1, and it is what the document recommends for clutter modelling.

Therefore: **`Aev = Am`**.

### Am formula (P.833-9 §2.1, Equation 2)

```
Am = A1 · f^α     (f in MHz)
```

Three sets of measured (A1, α) are cited in the document:

| Location | Frequency range | Tree height | RX height | A1 (dB) | α |
|----------|----------------|-------------|-----------|---------|---|
| Rio de Janeiro, Brazil | 900–1 800 MHz | 15 m | 2.4 m | 0.18 | 0.752 |
| Mulhouse, France | 900–2 200 MHz | 15 m | 1.6 m | 1.15 | 0.43 |
| St. Petersburg, Russia | 105.9–2 117.5 MHz | 12–16 m | 1.5 m | 1.37 | 0.42 |

**Implementation uses St. Petersburg: A1 = 1.37, α = 0.42.** Rationale: widest
frequency range, matches Table 1 (also St. Petersburg), RX height (1.5 m)
representative of a ground-level mobile terminal.

### Am dependence on vertical antenna–canopy distance

P.833-9 §2.1 states Am "depends on the species and density of the vegetation, plus
the antenna pattern of the terminal within the vegetation and **the vertical
distance between the antenna and the top of the vegetation**." The document
acknowledges this dependence but **provides no formula for it**. The (A1, α) fits
are ensemble measurements at fixed receiver heights. No h_rx scaling below the
canopy can be implemented without going beyond the document.

The only h_rx check within scope: P.833-9 §2.1 is scoped to "one terminal located
within woodland." A terminal at or above the canopy top is not within woodland.

---

## Numeric behaviour: saalos vs. P.833

### What saalos actually returns

`MAX_CLUTTER_LOSS = 22.0` (`clutter/constants.py:5`). `saalos.py:142–145` clamps
every result to it. The below-canopy formula (the only branch that fires, since
`h_tx` is always passed as `cch_m` in `advanced.py:64`) produces `arte > 22 dB`
at any distance greater than ~0.45 m. Every practical call to saalos returns
**exactly 22.0 dB**, with no frequency dependence and no h_rx sensitivity.

### Comparison table (cch=12 m, h_rx=2 m, any practical distance)

| f (MHz) | saalos | P.833 Am | Δ |
|---------|--------|----------|---|
| 450     | 22.0 dB | 17.3 dB | P.833 −4.7 dB |
| 900     | 22.0 dB | 23.1 dB | P.833 +1.1 dB |
| 1 800   | 22.0 dB | 30.8 dB | P.833 +8.8 dB |
| 2 600   | 22.0 dB | 37.2 dB | P.833 +15.2 dB |
| any, h_rx ≥ cch | 22.0 dB | 0.0 dB | P.833 correctly returns 0 |

**Behavioural change:** users below ~850 MHz will see less vegetation clutter loss;
users above 1 GHz will see more. Both directions are physically correct — saalos
could not model this because it was always clamped to a single constant.

---

## Implementation

### Function signature

```python
def clutter_loss_p833(cch_m: float, h_rx_m: float, f_mhz: float) -> float:
```

`d_m` is dropped — not used by the Am model.
`pol` is dropped — P.833-9 §2.1 provides no polarisation-dependent Am formula.

### Scalar implementation

```python
def clutter_loss_p833(cch_m: float, h_rx_m: float, f_mhz: float) -> float:
    """Vegetation clutter loss, ITU-R P.833-9 §2.1.

    Returns Am when h_rx < cch, 0 otherwise.
    Am = A1 * f^alpha is the maximum woodland attenuation (P.833-9 §2.1 Eq. 2),
    defined as "equivalent to the clutter loss often quoted for a terminal
    obstructed by some form of ground cover or clutter."
    A1=1.37, alpha=0.42 is the St. Petersburg fit (P.833-9 §2.1, 105.9-2117.5 MHz).
    """
    if h_rx_m >= cch_m:
        return 0.0
    return 1.37 * (f_mhz ** 0.42)
```

### Vectorised path (inline in `clutter/p833.py`)

```python
def clutter_loss_p833_vec(cch_m, h_rx_m, f_mhz):
    """Vectorised clutter_loss_p833. Inputs broadcast to common shape."""
    import numpy as np
    cch = np.asarray(cch_m, dtype=np.float64)
    hrx = np.asarray(h_rx_m, dtype=np.float64)
    f   = np.asarray(f_mhz,  dtype=np.float64)
    return np.where(hrx < cch, 1.37 * (f ** 0.42), 0.0)
```

Both functions live in `clutter/p833.py`. No separate `_p833_vec.py` needed.

### Frequency validity

The St. Petersburg fit is validated for **105.9–2 117.5 MHz**. Add a comment in
the implementation noting extrapolation outside this range.

---

## Am cross-check against P.833-9 Table 1

| f (MHz) | Table 1 Am (dB) | Formula Am (dB) | Δ |
|---------|----------------|-----------------|---|
| 105.9   | 9.4            | 8.7             | 0.7 |
| 466.5   | 18.0           | 17.5            | 0.5 |
| 949.0   | 26.5           | 23.2            | 3.3 |
| 1 852   | 29.0           | 30.7            | 1.7 |
| 2 118   | 34.1           | 33.3            | 0.8 |

Largest divergence is 3.3 dB at 949 MHz, within typical vegetation measurement
scatter (Mulhouse campaign standard deviation: 8.7 dB per P.833-9 §2.1).

---

## File inventory

### Create

| File | Contents |
|------|----------|
| `clutter/p833.py` | `clutter_loss_p833` (scalar) and `clutter_loss_p833_vec` (vectorised) |
| `tests/test_clutter_p833.py` | See §Tests below |

### Modify

**`clutter/categories.py:55`**
- `"model": "saalos"` → `"model": "p833"`

**`clutter/advanced.py`**
- Replace `from NoWires.clutter.saalos import clutter_loss_saalos` with
  `from NoWires.clutter.p833 import clutter_loss_p833`.
- In `compute_advanced_loss`: replace the `if model == "saalos":` block (lines
  60–70) with a `if model == "p833":` block calling `clutter_loss_p833(cch_m,
  ant_h_m, context.frequency_mhz)`.
- In `compute_terminal_clutter_loss`: remove the duplicate saalos block
  (lines 126–135). Extend the existing p2108 delegation (lines 136–138) to cover
  p833: `if model in ("p833", "p2108_height_gain", "p2108_combined"):`.
  The `if context.distance_m <= 0.0: return 0.0` guard (line 124) is no longer
  needed for p833 but can remain as a guard for p2108 §3.2.
- In `compute_path_clutter_loss`: delete both saalos special cases (lines 153–159).
  P.833 returns `ClutterComponents(Am, 0.0, "p833")`; with `path_loss_db = 0.0`
  it falls through correctly to `return hg_total` (line 162).
- In `compute_terminal_clutter_losses`: remove `both_saalos` (line 203) — dead
  code. When both endpoints are vegetation, `term_sum = 2·Am > 0` so the
  `term_sum > 0.0` branch always fires. Simplify line 204 to
  `if term_sum > 0.0:`.
- Update `ClutterComponents` model label strings from `"saalos"` to `"p833"`.

**`clutter/context.py`**
- Remove `polarization: int = 0` field — only consumed by saalos.
- Remove `rx_ground_elevation_m: float = 0.0` field — only consumed by saalos.
- Remove `tx_ground_elevation_m: float = 0.0` field — only consumed by saalos.
- Update `build_initial_clutter_context` and `build_link_clutter_context`
  factories to stop accepting/passing these three fields.

**`clutter/constants.py`**
- Remove `MAX_CLUTTER_LOSS = 22.0`. Its only consumer in the clutter pipeline is
  saalos (which is being deleted). `p833.py` must not import or apply it —
  Am is a model output, not a cap. Confirm no other file imports this constant
  before deleting (grep `MAX_CLUTTER_LOSS` across the repo).

**`clutter/__init__.py`**
- Remove `clutter_loss_saalos`, `clutter_loss_saalos_vec`, `_saalos_pol` exports.
- Add `clutter_loss_p833`, `clutter_loss_p833_vec` exports.

**`radio_coverage/engine.py`**
- Delete `_build_rx_ground_grid` (lines 37–65) entirely. It existed solely to
  populate `rx_ground_elevation_m` per pixel for saalos.
- Remove the `rx_ground_grid` parameter from `build_coverage_tasks` call.
- In `_compute_tx_clutter_loss`: remove the advanced-mode skip guard (comment
  "distance=0 would be wrong"). P.833 has no distance term; TX clutter can be
  precomputed in advanced mode identically to simple mode.

**`radio_coverage/tasks.py`**
- Remove `rx_ground_m = float(rx_ground_grid[i, j]) ...` per-pixel extraction
  (advanced mode pixel loop).
- Remove `rx_ground_elevation_m` and `tx_ground_elevation_m` from the
  per-pixel `ClutterLossContext(...)` construction.
- Remove `polarization` from the per-pixel context construction.
- Remove `rx_ground_grid` parameter from `build_coverage_tasks`.

**`p2p/compute.py`** and **`batch/outputs.py`**
- Remove `polarization` from `build_link_clutter_context` calls (or confirm
  `build_link_clutter_context` no longer accepts it after context.py is updated).
- No ground elevation removal needed here — `tx_elev` and `rx_elev` are passed
  for ITM, not for clutter.

**`tests/test_clutter_advanced.py`**
- Update `@patch` target: `clutter.advanced.clutter_loss_saalos` →
  `clutter.advanced.clutter_loss_p833`.
- Remove `d__meter`, `h_tx__meter`, `h_rx_gnd__meter`, `pol` from mock
  argument assertions.
- Update expected model string from `"saalos"` to `"p833"`.

**`tests/test_clutter_edge_coverage.py`**
- Replace `clutter_loss_saalos(...)` calls with `clutter_loss_p833(...)`.
- Remove `d_m`, `h_tx_m`, `h_rx_gnd_m`, `pol` arguments.

**`tests/test_clutter_math_snapshot.py`**
- Recompute and update snapshot values for the vegetation category at each
  tested frequency.

**`tests/test_clutter_categories.py:46,51`**
- Replace `"saalos"` with `"p833"` in the valid-model set assertion (line 46).
- Update `assert CLUTTER_CATEGORY_PARAMS["vegetation"]["model"] == "saalos"` →
  `== "p833"` (line 51).

**`tests/test_clutter.py:214`**
- Rename `test_advanced_helper_saalos_for_vegetation` and update its body to
  exercise `clutter_loss_p833` and expect model string `"p833"`.

**`tests/test_clutter_pipeline.py:125`**
- Rename the "saalos hot path" performance test and lower the timing threshold:
  P.833 is a single multiply; the 3.0 s budget was sized for saalos iterations.

**`tests/test_clutter_context.py`**
- Remove all assertions on `polarization`, `rx_ground_elevation_m`, and
  `tx_ground_elevation_m` (lines 20–21, 34, 39, 84–85, 88, 130, 136–137).
- Remove those keyword arguments from every `ClutterLossContext(...)` and factory
  call in the test file.

**`tests/_qgis_mocks.py:465`**
- Change `"clutter.saalos"` → `"clutter.p833"` in the module allowlist.

**`comparison/panel.py:104–105`**
- Remove `tx_ground_elevation_m=float(tx_ground)` and `polarization=p.polarization`
  from the `build_initial_clutter_context(...)` call. These keyword arguments will
  no longer exist after `context.py` is updated.

**`algorithm/_coverage_helpers.py:56–57`**
- Remove `tx_ground_elevation_m=tx_ground` and `polarization=p.polarization`
  from the `build_initial_clutter_context(...)` call. Same reason.

**`radio_coverage/engine.py:96`**
- Update the comment `"Advanced mode recomputes TX clutter per pixel (saalos /
  §3.2 depend on..."` to reflect that only P.2108 §3.2 has a distance dependency;
  P.833 does not.

**`Technical_Documentation.md`**
- Line 93: module description `"saalos + P.2108 §3.1/§3.2"` → `"P.833-9 §2.1 + P.2108 §3.1/§3.2"`.
- Line 114: module listing `clutter/saalos.py` → `clutter/p833.py`.
- Line 553: advanced clutter description — remove "distance" and "polarization"
  from the P.833 inputs; update algorithm name.
- Lines 587, 652–654: Decision D9 / invocation geometry — rewrite to describe
  P.833 Am; remove ITWOM 3.0 / Rust crate provenance.
- Lines 675, 681, 683: `method` field examples — replace `"saalos"` with `"p833"`.
- Line 709: table row `vegetation | saalos | ...` → `vegetation | p833 | ...`.

**`USERS-GUIDE.md`**
- Line 327: remove the performance note "Advanced clutter mode adds a saalos
  calculation per coverage pixel for vegetation cells... several seconds." P.833
  is a single multiply and adds no measurable overhead.
- Line 358: `clutter_method` field description — replace `"§3.1+§3.2/saalos"`
  example with `"§3.1+§3.2/p833"`.

**`README.md:23,92,103,235`**
- Replace four references to "saalos" in the advanced clutter mode description
  with "ITU-R P.833-9 §2.1 vegetation model".

**`NOTICE.md §7`**
- Replace with P.833 attribution note (see §NOTICE below).

### Delete

| File | Reason |
|------|--------|
| `clutter/saalos.py` | Replaced by `clutter/p833.py` |
| `clutter/_saalos_vec.py` | Replaced; vectorised path inlined in `clutter/p833.py` |
| `tests/test_clutter_saalos.py` | Superseded by `test_clutter_p833.py` |
| `tests/test_saalos_nan_guard.py` | Saalos-specific; not applicable to Am formula |
| `tests/test_saalos_above_canopy_nan.py` | Above-canopy branch does not exist in P.833 |
| `tests/test_clutter_constants.py` | Tests `MAX_CLUTTER_LOSS == 22.0`; constant is deleted with saalos |

---

## `clutter/advanced.py` call site diff

Current (×2 — `compute_advanced_loss:61–69` and `compute_terminal_clutter_loss:127–134`):
```python
loss = clutter_loss_saalos(
    d__meter=context.distance_m,
    cch__meter=cch_m,
    h_tx__meter=cch_m,
    h_rx__meter=ant_h_m,
    h_rx_gnd__meter=_terminal_ground_elev_m(terminal, context),
    pol=context.polarization,
    f__mhz=context.frequency_mhz,
)
return ClutterComponents(loss, 0.0, "saalos")
```

Replacement (×1 — only in `compute_advanced_loss`; `compute_terminal_clutter_loss`
delegates to `compute_advanced_loss` as described above):
```python
loss = clutter_loss_p833(
    cch_m=cch_m,
    h_rx_m=ant_h_m,
    f_mhz=context.frequency_mhz,
)
return ClutterComponents(loss, 0.0, "p833")
```

---

## Tests to write (`tests/test_clutter_p833.py`)

| Test | What it checks |
|------|----------------|
| `test_zero_when_rx_at_canopy` | `h_rx == cch` → 0.0 dB |
| `test_zero_when_rx_above_canopy` | `h_rx > cch` → 0.0 dB |
| `test_positive_loss_below_canopy` | `h_rx < cch` → loss > 0 |
| `test_distance_independent` | result identical for any two distinct `d_m` values (Am has no d term; confirm no accidental coupling) |
| `test_increases_with_frequency` | Am increases as f increases (f^0.42 monotone) |
| `test_am_reference_900mhz` | `clutter_loss_p833(12, 2, 900)` ≈ 23.1 dB (1.37 · 900^0.42) |
| `test_am_reference_1800mhz` | `clutter_loss_p833(12, 2, 1800)` ≈ 30.8 dB |
| `test_scalar_vec_agreement` | scalar and vectorised agree to floating-point equality |
| `test_vec_broadcasts` | vectorised handles arrays of cch, h_rx, f |
| `test_no_max_clutter_loss_cap` | result at 2600 MHz ≈ 37.2 dB — confirm it is NOT capped at 22 dB |

---

## NOTICE.md §7 replacement text

```markdown
## 7. Vegetation Clutter Model — ITU-R P.833

The vegetation clutter-loss model in `clutter/p833.py` implements the Am
(maximum woodland attenuation) value from §2.1 of ITU-R Recommendation P.833-9
(2016), "Attenuation in vegetation." P.833-9 §2.1 states that Am is "equivalent
to the clutter loss often quoted for a terminal obstructed by some form of ground
cover or clutter." Am = A1 · f^α uses the St. Petersburg fit (A1=1.37, α=0.42)
cited in P.833-9 §2.1 for mixed coniferous-deciduous forest, 105.9–2117.5 MHz.
The implementation is original code; no third-party source code was used.

ITU-R Recommendations are freely published by the International Telecommunication
Union.
```

---

## CHANGELOG entry

```
- Replace saalos vegetation clutter model with ITU-R P.833-9 §2.1 Am.
  Removes files derived from ITWOM 3.0 (Shumate / Givens & Bell); replaces with
  original code based on a publicly available ITU Recommendation. Removes
  clutter/saalos.py, clutter/_saalos_vec.py, and three saalos-specific test files.
  Removes dead clutter pipeline fields (polarization, rx/tx_ground_elevation_m
  in ClutterLossContext) and the per-pixel rx_ground_grid DEM pass in the coverage
  engine. Vegetation clutter loss is now frequency-dependent and bounded by Am
  (23 dB at 900 MHz, 31 dB at 1800 MHz); saalos was frequency-independent and
  always capped at MAX_CLUTTER_LOSS = 22 dB.
```

---

## Implementation order

1. Create `clutter/p833.py` (scalar + vectorised).
2. Write `tests/test_clutter_p833.py`; confirm all tests pass.
3. Update `clutter/categories.py` and `clutter/advanced.py` (model switch, dead
   code removal, call site simplification).
4. Update `clutter/context.py` (remove three dead fields and update both factory
   signatures).
5. Update `clutter/constants.py` (remove `MAX_CLUTTER_LOSS` — first grep the full
   repo to confirm `test_clutter_constants.py` is the only non-saalos consumer).
6. Update `clutter/__init__.py`.
7. Update call sites for the removed context factory fields:
   - `radio_coverage/engine.py` (remove `_build_rx_ground_grid`, update TX clutter
     guard comment)
   - `radio_coverage/tasks.py` (remove ground elevation and polarization from
     per-pixel context construction)
   - `comparison/panel.py` (remove `tx_ground_elevation_m`, `polarization`)
   - `algorithm/_coverage_helpers.py` (same)
   - `p2p/compute.py` and `batch/outputs.py` (confirm factory calls compile)
8. Update test files that reference removed fields or the "saalos" string:
   - `tests/test_clutter_advanced.py`
   - `tests/test_clutter_edge_coverage.py`
   - `tests/test_clutter_math_snapshot.py`
   - `tests/test_clutter_categories.py`
   - `tests/test_clutter.py`
   - `tests/test_clutter_pipeline.py`
   - `tests/test_clutter_context.py`
   - `tests/_qgis_mocks.py`
9. Delete `clutter/saalos.py`, `clutter/_saalos_vec.py`, and four test files
   (`test_clutter_saalos.py`, `test_saalos_nan_guard.py`,
   `test_saalos_above_canopy_nan.py`, `test_clutter_constants.py`).
10. Replace `NOTICE.md §7`.
11. Update docs:
    - `Technical_Documentation.md` (7 locations)
    - `USERS-GUIDE.md` (2 locations)
    - `README.md` (4 locations)
12. Run full test suite; confirm no regressions outside the deleted saalos tests.
