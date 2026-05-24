#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Repeater-mode coverage: RF-7800V-HH at 47 MHz, 10W, 30m tower, fixed site antenna."""
import os
import sys
import time

from qgis.core import QgsApplication, QgsProcessingContext, QgsProcessingFeedback
from NoWires.provider import NoWiresProvider

OUTPUT_DIR = "/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


class LogFeedback(QgsProcessingFeedback):
    def pushInfo(self, info):          print(f"  {info}")
    def pushWarning(self, warning):    print(f"  [W] {warning}")
    def pushDebugInfo(self, info):     pass
    def reportError(self, error, fatal_error=False):
        print(f"  [{'FATAL' if fatal_error else 'ERR'}] {error}")
    def setProgressText(self, text):    pass


_BASE_PARAMS = {
    "TX_POINT": "125.66038991061612,7.154183359138755 [EPSG:4326]",
    "TX_HEIGHT": 30.0,
    "RX_HEIGHT": 1.5,
    "FREQ_MHZ": 47.0,
    "RADIUS_KM": 50.0,
    "GRID_SIZE": 7,
    "POLARIZATION": 1,
    "CLIMATE": 0,
    "TX_POWER": 40.0,
    "TX_GAIN": 4.0,
    "RX_GAIN": 0.0,
    "CABLE_LOSS": 1.5,
    "RX_SENSITIVITY": -116.0,
    "ANTENNA_PRESET": 0,
    "ANTENNA_BW": 360.0,
    "ANTENNA_AZ": 0.0,
    "FRONT_BACK_DB": 25.0,
    "DOWNTILT_DEG": 0.0,
    "H_PATTERN": "",
    "V_PATTERN": "",
    "CLUTTER_MODEL": 1,
    "CLUTTER_RASTER": "",
    "TX_CLUTTER_OVERRIDE": 0,
    "RX_CLUTTER_OVERRIDE": 0,
    "CCH_OVERRIDE": 0.0,
    "CLUTTER_PERCENTILE": 50.0,
    "STREET_WIDTH": 27.0,
    "BEL_ENABLED": False,
    "BEL_BUILDING_TYPE": 0,
    "BEL_ELEVATION_ANGLE": 0.0,
    "N0": 301.0,
    "EPSILON": 15.0,
    "SIGMA": 0.005,
    "OUTPUT_REPORT_PDF": "",
}

SCENARIOS = [
    {
        "label": "90/50/50 (time-critical, median loc/sit)",
        "stem": "7800h_repeater_90-50-50_1024",
        "time_pct": 90.0, "location_pct": 50.0, "situation_pct": 50.0,
    },
    {
        "label": "90/70/70 (balanced fixed TX, mobile RX)",
        "stem": "7800h_repeater_90-70-70_1024",
        "time_pct": 90.0, "location_pct": 70.0, "situation_pct": 70.0,
    },
]


def run_scenario(alg, label, stem, time_pct, location_pct, situation_pct):
    params = dict(_BASE_PARAMS)
    params["TIME_PCT"] = time_pct
    params["LOCATION_PCT"] = location_pct
    params["SITUATION_PCT"] = situation_pct
    params["OUTPUT_RASTER"] = os.path.join(OUTPUT_DIR, f"{stem}.tif")
    params["OUTPUT_REPORT_CSV"] = os.path.join(OUTPUT_DIR, f"{stem}.csv")
    params["OUTPUT_REPORT_JSON"] = os.path.join(OUTPUT_DIR, f"{stem}.json")
    params["OUTPUT_REPORT_HTML"] = os.path.join(OUTPUT_DIR, f"{stem}.html")

    print(f"\n{'='*55}")
    print(f"  {label}")
    print(f"{'='*55}")
    print(f"  TX: 4 dBi ant, 1.5 dB coax → EIRP = {40.0+4.0-1.5:.1f} dBm")

    ctx = QgsProcessingContext()
    feedback = LogFeedback()
    t0 = time.monotonic()

    try:
        result = alg.run(params, context=ctx, feedback=feedback)
    except Exception as exc:
        print(f"  [FATAL] {exc}")
        return None

    elapsed = time.monotonic() - t0
    r, ok = result if isinstance(result, tuple) else (result, True)
    print(f"  Done in {elapsed:.1f}s, success={ok}")
    return r


def main():
    print("=" * 55)
    print("  NoWires — RF-7800V-HH REPEATER MODE (Fixed Site)")
    print("  TX: 47 MHz, 10W, 30m tower, 4 dBi antenna, 1.5 dB coax")
    print("  RX: 1.5m handheld, 0 dBi whip, −116 dBm FM")
    print("  EIRP = 42.5 dBm  |  Simple clutter")
    print("=" * 55)

    app = QgsApplication([], False)
    app.initQgis()

    provider = NoWiresProvider()
    app.processingRegistry().addProvider(provider)
    alg = app.processingRegistry().algorithmById("nowires:coverage_analysis")
    if alg is None:
        print("ERROR: algorithm not found")
        app.exitQgis()
        sys.exit(1)

    results = {}
    for s in SCENARIOS:
        r = run_scenario(alg, s["label"], s["stem"],
                         s["time_pct"], s["location_pct"], s["situation_pct"])
        if r:
            csv = r.get("OUTPUT_REPORT_CSV")
            if csv and os.path.exists(csv):
                # extract key metrics
                d = {}
                with open(csv) as f:
                    for line in f:
                        parts = line.strip().split(",")
                        if len(parts) >= 3 and parts[0] == "results":
                            d[parts[1]] = parts[2]
                results[s["label"]] = d

    app.exitQgis()

    print(f"\n{'='*55}")
    print("  REPEATER MODE — SUMMARY")
    print(f"{'='*55}")
    header = f"  {'Scenario':<32} {'>−116dBm':>9} {'Mean Prx':>9} {'Avg Dist':>9} {'Loss':>8} {'Reliability':>13}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for label, d in results.items():
        pct = float(d.get("pct_above_sensitivity", 0))
        mean = float(d.get("mean_prx_dbm", 0))
        dist = float(d.get("average_distance_km", 0))
        loss = float(d.get("total_path_loss_db", 0))
        rel = d.get("reliability_summary", "")
        print(f"  {label:<32} {pct:>8.1f}% {mean:>9.1f} {dist:>9.1f} {loss:>8.1f} {rel:>13}")

    # Compare with handheld 50/50/50 for reference
    print("\n  Reference — handheld 50/50/50 (whip, no coax): 78.6% @ −103.7 dBm / 31.0 km")
    print("  Reference — handheld 90/90/90 (whip, no coax): 47.6% @ −117.6 dBm / 26.2 km")
    print("  Repeater EIRP advantage vs handheld: +2.5 dB (4 dBi ant − 1.5 dB coax)")

    print("\nDone.")
    for fname in sorted(os.listdir(OUTPUT_DIR)):
        p = os.path.join(OUTPUT_DIR, fname)
        if "repeater" in fname and fname.endswith(".tif"):
            print(f"  {fname}  ({os.path.getsize(p)/1048576:.1f} MB)")


if __name__ == "__main__":
    main()
