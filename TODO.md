# NoWires Plugin TODO

## 1. Better Antenna Modeling

Add antenna presets and patterns:
- omni / sector / dish
- front-to-back ratio
- downtilt / uptilt
- optional horizontal and vertical pattern files

This would improve both realism and link-design usefulness, especially for fixed wireless and sector planning workflows.

## 2. Clutter / Land-Cover Losses

### Final Recommendation

Implement clutter / land-cover loss as an optional terminal correction layer on top of ITM, using ESA WorldCover for land cover, and do not depend on `itur` for this part.

### Why This Is the Right Shape

- Keeps the current DEM + ITM core intact.
- Matches the first-order way clutter is commonly handled in practice: extra loss near the terminals, not a full replacement propagation model.
- Avoids pulling in `itur` for something it does not really cover well.
- Uses a free, globally available land-cover dataset.

### Data Source

- ESA WorldCover land-cover raster
- Free to access; practical sources include ESA/Terrascope and AWS-hosted copies
- Use it as a tiled raster input much like elevation, but for classification instead of height

### Model Design

1. Sample land cover around the TX terminal.
2. Sample land cover around the RX terminal or coverage pixel endpoint.
3. Map raw land-cover classes into a smaller propagation-oriented clutter category:
   - `open`
   - `rural`
   - `vegetation`
   - `suburban`
   - `urban`
4. Apply an excess clutter loss after ITM:
   - `total_loss_db = itm_loss_db + clutter_tx_db + clutter_rx_db`
5. Keep it optional and user-visible:
   - `Off`
   - `Simple clutter correction`

### Initial Loss Table

Start simple and tunable:
- `open`: `0 dB`
- `rural`: `2 dB`
- `vegetation`: `6 dB`
- `suburban`: `8 dB`
- `urban`: `10 dB`

These are MVP values, not sacred truth. The key is to begin with a clear, explainable model.

### Implementation Scope

Add a new module, for example `clutter.py`, with functions like:
- `worldcover_class_to_clutter_category(class_id)`
- `clutter_loss_db(category, frequency_mhz)`
- `sample_terminal_clutter(...)`
- `compute_terminal_clutter_losses(...)`

Integrate it in:
- P2P: after the ITM result is computed
- Coverage: fixed TX clutter per run, varying RX clutter per pixel

### Plugin Parameters

Add:
- `ENABLE_CLUTTER`
- `CLUTTER_MODEL`
- optional overrides:
  - `TX_CLUTTER_OVERRIDE`
  - `RX_CLUTTER_OVERRIDE`

This lets users force a category when the raster is wrong or unavailable.

### Outputs

Expose in results and reporting:
- `itm_loss_db`
- `clutter_tx_db`
- `clutter_rx_db`
- `total_path_loss_db`

For coverage summaries, mention whether clutter was enabled and which source was used.

### What Not To Do In v1

- Do not sample clutter all along every path.
- Do not use `itur` for this feature.
- Do not jump straight to a heavy standards-based clutter engine.
- Do not hide the correction from the user.

### Future v2

If a more formal microwave-oriented model is needed later:
- add a standards-based path where valid
- possibly use ITU-style corrections for supported frequency ranges
- keep the simple WorldCover-based fallback for lower bands and general-purpose use

### Summary

Use ESA WorldCover plus a custom terminal clutter correction module, layered on top of ITM, with simple configurable excess-loss categories in v1. `itur` is useful elsewhere, but not as the core of this land-cover/clutter feature.

## 3. Link Reliability Outputs

Build clearer user-facing outputs around the existing ITM variability inputs:
- fade margin classification
- availability estimate
- service / marginal / unreliable summaries

This would make results easier to interpret without forcing users to manually translate raw path-loss numbers into operational meaning.

## 4. Coverage Comparison Mode

Allow users to run and compare two coverage analyses:
- before / after antenna height
- frequency A vs. frequency B
- omni vs. sector
- delta raster in dB

This would be especially useful for engineering tradeoff studies and quick planning iterations.

## 5. TX/RX Map Layers For P2P

Create explicit TX and RX point layers with useful attributes:
- role
- antenna type
- height
- gain

This would make point-to-point outputs easier to inspect, symbolize, label, and reuse in QGIS workflows.

## 6. Better Report Export

Add one-click export for P2P and coverage summaries:
- CSV
- JSON
- printable HTML or PDF
- include assumptions and key inputs

This would help users share analysis results without manually collecting values from the UI.

## 7. Batch Analysis

Add support for:
- one TX to many RX points
- many candidate sites to one RX
- site ranking by link margin, loss, or clearance

This is likely the biggest payoff feature for actual network-planning workflows.

## 8. Profile Chart Improvements

Improve the existing profile chart with:
- hover values
- obstruction callouts
- toggle lines and zones
- export image and data

The chart is already useful, and this would make it much better for practical review and reporting.

## 9. Native Benchmark And Performance Guardrails

Extend the current benchmark work into:
- a couple of named reference cases
- performance notes in docs
- optional CI smoke benchmark so regressions are visible

This would make future performance work less guessy and more measurable.

## 10. Windows 3D Fallback UX

Because plugin-side 3D launch is unsafe on Windows, improve the fallback flow:
- clearer message
- helper behavior that selects or highlights the tracked DEM and coverage layers
- brief guidance on opening the native QGIS 3D view

This would make the current Windows limitation less confusing and less frustrating for users.
