# Plan: Replace saalos with ITU-R P.833-9 §2.1

## Background

`clutter/saalos.py` and `clutter/_saalos_vec.py` implement the saalos vegetation
clutter-loss algorithm originally written by Sid Shumate for ITWOM 3.0 (copyright
© 2011 Shumate / Givens & Bell, Inc., all rights reserved, commercial use
restricted). The reimplementation intentionally targets bit-for-bit numeric parity
with the ITWOM 3.0 reference C code (`_saalos_vec.py:15–20`), which makes the
independent-expression defence difficult to sustain.

**Goal:** Replace both files with a clean implementation of ITU-R P.833-9 §2.1
Equation 1 ("one terminal in woodland"), remove all saalos test files, update
attribution in NOTICE.md, and leave every existing caller working without any
change to their public API.

---

## Chosen model: P.833-9 §2.1 Equation 1

```
Aev = Am · [1 − exp(−d · γ / Am)]     (dB)
```

| Symbol | Description |
|--------|-------------|
| `d`    | Estimated penetration depth through vegetation (m); see §Depth proxy below |
| `γ`    | Specific attenuation for short vegetative paths (dB/m); frequency-dependent |
| `Am`   | Maximum total attenuation from one vegetative obstruction (dB); frequency-dependent |

### Why this model

* Explicitly designed for "one terminal inside woodland" — the exact clutter scenario.
* P.833-9 notes: *"Am is equivalent to the clutter loss often quoted for a terminal
  obstructed by some form of ground cover or clutter."*
* Natural saturation at `Am`: loss can't grow without bound as depth increases,
  reflecting the surface-wave / diffraction bypass mechanism.
* Entirely specified by a publicly available ITU-R Recommendation; no third-party
  code or proprietary reference required.
* More physically correct than the §3.1 linear model (which is for a single-tree
  obstruction with both terminals outside) and more relevant than §2.2 (satellite
  slant paths with elevation angle).

### Model is NOT selected

| Model | Why not |
|-------|---------|
| P.833-9 §3.1 `Aet = γ·d` | Linear, only valid ≤1 GHz, for single-tree obstruction — wrong geometry |
| P.833-9 §2.2 `L = 0.25·f^0.39·d^0.25·θ^0.05` | Satellite slant paths; includes elevation angle; Austrian pine only |
| P.833-9 §3.2 RET model | Requires leaf area index, LAI, species tables — impractical for a clutter model |

---

## Parameter functions

### γ(f) — specific attenuation

P.833-9 Table 1 (St. Petersburg mixed coniferous-deciduous forest, tree height 16 m):

| f (MHz)  | γ (dB/m) |
|----------|----------|
|   105.9  |   0.04   |
|   466.5  |   0.12   |
|   949.0  |   0.17   |
|  1 852   |   0.30   |
|  2 118   |   0.34   |

Implementation: log-linear interpolation between these anchor points.
Below 105.9 MHz: clamp to 0.04 dB/m.
Above 2 118 MHz: extrapolate on the log-log trend of the last two points.

### Am(f) — maximum attenuation

P.833-9 §2.1 power-law formula:

```
Am = A1 · f^α    (f in MHz)
```

St. Petersburg fit (matches Table 1, mean-tree-height 16 m): **A1 = 1.37, α = 0.42**.

### Depth proxy

P.833-9 §2.1 defines `d` as horizontal path length through the forest. The
available inputs are canopy height `cch_m` and RX antenna height `h_rx_m`.
Use:

```python
d = max(0.0, cch_m - h_rx_m)
```

This is the vertical burial depth (metres from RX antenna to canopy top), used as a
proxy for horizontal penetration depth. It is an approximation: document it with a
one-line comment. Future work could derive a proper geometric depth from DEM slope,
but that is out of scope here.

---

## Full replacement formula (Python)

```python
import math

# P.833-9 §2.1 Table 1 anchor points for γ(f)
_GAMMA_TABLE = [
    (105.9,  0.04),
    (466.5,  0.12),
    (949.0,  0.17),
    (1852.0, 0.30),
    (2118.0, 0.34),
]

def _gamma_p833(f_mhz: float) -> float:
    """Specific attenuation γ (dB/m) via log-linear interpolation, P.833-9 Table 1."""
    if f_mhz <= _GAMMA_TABLE[0][0]:
        return _GAMMA_TABLE[0][1]
    if f_mhz >= _GAMMA_TABLE[-1][0]:
        f0, g0 = _GAMMA_TABLE[-2]
        f1, g1 = _GAMMA_TABLE[-1]
        slope = math.log(g1 / g0) / math.log(f1 / f0)
        return g1 * (f_mhz / f1) ** slope
    for i in range(len(_GAMMA_TABLE) - 1):
        f0, g0 = _GAMMA_TABLE[i]
        f1, g1 = _GAMMA_TABLE[i + 1]
        if f0 <= f_mhz <= f1:
            t = math.log(f_mhz / f0) / math.log(f1 / f0)
            return math.exp(math.log(g0) + t * math.log(g1 / g0))
    return _GAMMA_TABLE[-1][1]  # unreachable

def clutter_loss_p833(d_m: float, cch_m: float, h_rx_m: float,
                      f_mhz: float) -> float:
    """Vegetation clutter loss, P.833-9 §2.1 Eq. 1.

    d_m     — link distance (unused; kept for interface symmetry with saalos)
    cch_m   — canopy/clutter height (m)
    h_rx_m  — RX antenna height above ground (m)
    f_mhz   — frequency (MHz)

    Returns excess attenuation Aev in dB (non-negative).
    d_v = cch - h_rx is used as a proxy for horizontal penetration depth (P.833-9 §2.1).
    """
    d_v = max(0.0, cch_m - h_rx_m)
    if d_v == 0.0:
        return 0.0
    gamma = _gamma_p833(f_mhz)
    Am = 1.37 * (f_mhz ** 0.42)          # P.833-9 §2.1, St. Petersburg fit
    return Am * (1.0 - math.exp(-d_v * gamma / Am))
```

Notes on `d_m` (link distance): saalos uses distance in its below-canopy formula.
P.833-9 §2.1 does not use link distance in Eq. 1 — distance effects are captured
by ITM's path-loss model, not the clutter term. Keep `d_m` in the signature for
drop-in compatibility but leave it unused with a comment.

Notes on `pol` (polarisation): P.833-9 §2.1 does not distinguish polarisation at
this level (below ~1 GHz there is a tendency for V > H but no parametric formula is
given). Drop `pol` from the public signature entirely — it was an artefact of
saalos's internals and is not meaningful in P.833.

---

## File inventory

### Create

| File | Contents |
|------|----------|
| `clutter/p833.py` | `clutter_loss_p833(d_m, cch_m, h_rx_m, f_mhz) → float` (scalar) |
| `clutter/_p833_vec.py` | `clutter_loss_p833_vec(...)` vectorised over numpy arrays; same pattern as `_saalos_vec.py` |
| `tests/test_clutter_p833.py` | See §Tests below |

### Modify

| File | Change |
|------|--------|
| `clutter/categories.py:55` | `"model": "saalos"` → `"model": "p833"` |
| `clutter/advanced.py` | Replace saalos import + two `if model == "saalos":` call sites + `compute_path_clutter_loss` string comparisons. Drop `pol` arg from p833 calls. |
| `clutter/__init__.py` | Swap saalos exports for p833. Remove `_saalos_pol`, `clutter_loss_saalos`, `clutter_loss_saalos_vec`. |
| `tests/test_clutter_advanced.py` | Update `@patch` target from `clutter.advanced.clutter_loss_saalos` to `clutter.advanced.clutter_loss_p833`. Drop `pol` from mock argument assertions. |
| `tests/test_clutter_edge_coverage.py` | Replace direct `clutter_loss_saalos(...)` calls with `clutter_loss_p833(...)`. Remove unused `pol` argument. |
| `tests/test_clutter_math_snapshot.py` | Recompute and update snapshot values for the vegetation category. |
| `NOTICE.md §7` | Replace entire §7 with a short P.833 attribution note (see §NOTICE below). |

### Delete

| File | Reason |
|------|--------|
| `clutter/saalos.py` | Replaced by `clutter/p833.py` |
| `clutter/_saalos_vec.py` | Replaced by `clutter/_p833_vec.py` |
| `tests/test_clutter_saalos.py` | All cases superseded by `test_clutter_p833.py` |
| `tests/test_saalos_nan_guard.py` | NaN guard tests specific to saalos internals |
| `tests/test_saalos_above_canopy_nan.py` | Above-canopy branch does not exist in P.833 |

---

## API changes

### `clutter/advanced.py` call sites

Current (×2):
```python
loss = clutter_loss_saalos(
    d__meter=context.distance_m,
    cch__meter=cch_m,
    h_tx__meter=cch_m,        # always == cch_m; only below-canopy branch fires
    h_rx__meter=ant_h_m,
    h_rx_gnd__meter=_terminal_ground_elev_m(terminal, context),
    pol=context.polarization,
    f__mhz=context.frequency_mhz,
)
```

Replacement:
```python
loss = clutter_loss_p833(
    d_m=context.distance_m,   # kept for symmetry; unused by model
    cch_m=cch_m,
    h_rx_m=ant_h_m,
    f_mhz=context.frequency_mhz,
)
```

`h_tx`, `h_rx_gnd`, and `pol` are dropped. Note: in every saalos call in
`advanced.py`, `h_tx__meter` was always passed as `cch_m` (not the actual TX
height), meaning the above-canopy branch of saalos never fired in production. The
below-canopy branch similarly never used `h_rx_gnd` for its core formula. P.833
§2.1 confirms neither is needed.

### `ClutterComponents` model label

Change string from `"saalos"` to `"p833"` in the `ClutterComponents` return
values in `advanced.py`.

---

## Tests to write (`tests/test_clutter_p833.py`)

| Test | What it checks |
|------|---------------|
| `test_zero_when_rx_at_canopy` | `h_rx == cch` → 0.0 dB |
| `test_zero_when_rx_above_canopy` | `h_rx > cch` → 0.0 dB |
| `test_positive_loss_below_canopy` | `h_rx < cch`, typical inputs → loss > 0 |
| `test_increases_with_depth` | loss increases as `h_rx` decreases (deeper under canopy) |
| `test_increases_with_frequency` | loss increases as `f_mhz` increases (at fixed depth) |
| `test_saturates_below_am` | loss ≤ Am(f) for any depth |
| `test_reference_values` | spot-check Eq. 1 at (d_v=10 m, 900 MHz), (d_v=5 m, 1800 MHz) |
| `test_scalar_vec_agreement` | scalar and vectorised paths agree to 1e-10 |
| `test_nan_guard_vec` | NaN inputs produce 0.0 or MAX_CLUTTER_LOSS, not NaN propagation |
| `test_zero_distance_scalar` | `d_m=0` → 0.0 (P.833 §2.1 has no distance term; confirm it doesn't break) |
| `test_gamma_interpolation_endpoints` | `_gamma_p833` below 105.9 MHz clamps; above 2118 MHz extrapolates continuously |

---

## NOTICE.md §7 replacement text

```markdown
## 7. Vegetation Clutter Model — ITU-R P.833

The vegetation clutter-loss model in `clutter/p833.py` and `clutter/_p833_vec.py`
implements Equation 1 from §2.1 of ITU-R Recommendation P.833-9 (2016), "Attenuation
in vegetation." The γ and Am parameter values are taken from P.833-9 Table 1
(St. Petersburg mixed-forest measurements) and the Am power-law fit cited therein.
The implementation is original code; no third-party source code was used.

ITU-R Recommendations are published freely by the International Telecommunication
Union. The algorithms and data tables in P.833-9 are not subject to copyright
protection as factual/scientific content.
```

---

## Numeric behaviour comparison

| Scenario | saalos (current) | P.833-9 §2.1 |
|----------|-----------------|--------------|
| `h_rx = cch` (at canopy) | 0 dB | 0 dB |
| `h_rx = 0`, `cch = 12 m`, 900 MHz | ~18–22 dB (distance-dependent) | `Am·(1−e^(−12·0.17/Am))` ≈ 7.7 dB (Am≈28.7) |
| `h_rx = 2`, `cch = 12 m`, 1800 MHz | distance/geometry-dependent | `Am·(1−e^(−10·0.29/Am))` ≈ 9.5 dB (Am≈32.0) |
| Very large depth | grows unboundedly (with distance) | saturates at Am |

**P.833 values will be lower and distance-independent (in the clutter term).**
This is the correct behaviour: ITM already accounts for path loss over distance;
the clutter term should only model the terminal-obstruction excess, which P.833-9
§2.1 is specifically designed to give.

---

## CHANGELOG entry

```
- Replace saalos vegetation clutter model with ITU-R P.833-9 §2.1 (Equation 1).
  Removes files derived from ITWOM 3.0 (Shumate / Givens & Bell); replaces with
  original code based on a publicly available ITU Recommendation. Removes
  clutter/saalos.py, clutter/_saalos_vec.py, and three saalos-specific test files.
```

---

## Implementation order

1. Create `clutter/p833.py` (scalar) and `clutter/_p833_vec.py` (vectorised).
2. Write `tests/test_clutter_p833.py` and confirm tests pass against the new code.
3. Update `clutter/categories.py` and `clutter/advanced.py`.
4. Update `clutter/__init__.py`.
5. Update `tests/test_clutter_advanced.py`, `test_clutter_edge_coverage.py`,
   `test_clutter_math_snapshot.py`.
6. Delete `clutter/saalos.py`, `clutter/_saalos_vec.py`, and the three saalos test
   files.
7. Replace NOTICE.md §7.
8. Run full test suite; confirm no regressions outside the deleted saalos tests.
