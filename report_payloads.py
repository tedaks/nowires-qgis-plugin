# -*- coding: utf-8 -*-
"""Pure-Python helpers for NoWires report payloads and marker outputs."""

from __future__ import annotations

import os
from pathlib import Path

from osgeo import ogr, osr
from .reliability import summarize_reliability


_OGR_DRIVER_BY_EXT = {
    ".shp": "ESRI Shapefile",
    ".gpkg": "GPKG",
    ".geojson": "GeoJSON",
    ".json": "GeoJSON",
    ".kml": "KML",
}


def ogr_driver_for_path(path):
    """Return the OGR driver name appropriate for ``path``'s extension.

    Defaults to GPKG when the extension is unknown — GPKG is the modern
    QGIS Processing default and tolerates the geometry types we write.
    """
    ext = os.path.splitext(str(path))[1].lower()
    return _OGR_DRIVER_BY_EXT.get(ext, "GPKG")


def _remove_existing_ogr_dataset(driver, path):
    """Best-effort removal of an existing OGR dataset before recreating it.

    Older GDAL releases let ``driver.Open`` return None for missing paths;
    GDAL 3.10+ raises ``RuntimeError`` instead. Using ``os.path.exists`` is
    portable across both.
    """
    str_path = str(path)
    if os.path.exists(str_path):
        try:
            driver.DeleteDataSource(str_path)
        except RuntimeError:
            # Driver couldn't reclaim the file (locked, partial, foreign
            # format) — fall back to a plain unlink.
            try:
                os.remove(str_path)
            except OSError:
                pass


def build_p2p_report_payload(
    tx_lat,
    tx_lon,
    rx_lat,
    rx_lon,
    tx_h,
    rx_h,
    f_mhz,
    polarization_name,
    climate_name,
    k_factor,
    dist_m,
    propagation_mode,
    propagation_mode_name,
    fspl_db,
    itm_loss_db,
    tx_power,
    tx_gain,
    rx_gain,
    cable_loss,
    eirp_dbm,
    prx_dbm,
    rx_sensitivity_dbm,
    margin_db,
    los_blocked,
    fresnel_1_violated,
    fresnel_60_violated,
    max_fresnel_radius_m,
    total_path_loss_db=None,
    clutter_tx_db=0.0,
    clutter_rx_db=0.0,
    clutter_source="off",
    tx_antenna_preset="omni",
    rx_antenna_preset="omni",
    antenna_gain_adjustment_db=0.0,
):
    """Build the structured P2P report payload."""
    reliability = summarize_reliability(
        margin_db=margin_db,
        frequency_mhz=f_mhz,
        distance_km=dist_m / 1000.0,
        los_blocked=los_blocked,
    )
    return {
        "report_type": "p2p",
        "generated_by": "NoWires",
        "inputs": {
            "tx_lat": round(tx_lat, 6),
            "tx_lon": round(tx_lon, 6),
            "rx_lat": round(rx_lat, 6),
            "rx_lon": round(rx_lon, 6),
            "tx_height_m": tx_h,
            "rx_height_m": rx_h,
            "frequency_mhz": f_mhz,
            "polarization": polarization_name,
            "climate": climate_name,
            "k_factor": round(k_factor, 6),
            "tx_power_dbm": tx_power,
            "tx_gain_dbi": tx_gain,
            "rx_gain_dbi": rx_gain,
            "cable_loss_db": cable_loss,
            "rx_sensitivity_dbm": rx_sensitivity_dbm,
            "tx_antenna_preset": tx_antenna_preset,
            "rx_antenna_preset": rx_antenna_preset,
            "clutter_source": clutter_source,
        },
        "results": {
            "distance_m": dist_m,
            "distance_km": round(dist_m / 1000.0, 3),
            "propagation_mode": propagation_mode,
            "propagation_mode_name": propagation_mode_name,
            "free_space_loss_db": fspl_db,
            "itm_path_loss_db": itm_loss_db,
            "excess_loss_db": itm_loss_db - fspl_db,
            "eirp_dbm": eirp_dbm,
            "clutter_tx_db": clutter_tx_db,
            "clutter_rx_db": clutter_rx_db,
            "total_path_loss_db": itm_loss_db if total_path_loss_db is None else total_path_loss_db,
            "antenna_gain_adjustment_db": antenna_gain_adjustment_db,
            "received_power_dbm": prx_dbm,
            "link_margin_db": margin_db,
            "availability_method": reliability["availability_method"],
            "availability_estimate_pct": reliability["availability_estimate_pct"],
            "fade_margin_class": reliability["fade_margin_class"],
            "reliability_summary": reliability["reliability_summary"],
            "los_blocked": bool(los_blocked),
            "fresnel_1_violated": bool(fresnel_1_violated),
            "fresnel_60_violated": bool(fresnel_60_violated),
            "max_fresnel_radius_m": max_fresnel_radius_m,
        },
        "status": {
            "summary": "VIABLE" if margin_db >= 0 else "NOT VIABLE",
            "viable": bool(margin_db >= 0),
        },
    }


def build_coverage_report_payload(
    tx_lat,
    tx_lon,
    tx_h,
    rx_h,
    f_mhz,
    radius_km,
    grid_size,
    polarization_name,
    climate_name,
    time_pct,
    location_pct,
    situation_pct,
    tx_power,
    tx_gain,
    rx_gain,
    cable_loss,
    rx_sensitivity_dbm,
    valid_pixel_count,
    pixel_count,
    min_prx_dbm,
    max_prx_dbm,
    mean_prx_dbm,
    pct_above_sensitivity,
    usable_cell_count,
    min_distance_km,
    max_distance_km,
    average_distance_km,
    clutter_model="Off",
    clutter_source="off",
    tx_antenna_preset="omni",
    itm_loss_db=None,
    clutter_tx_db=0.0,
    clutter_rx_db=0.0,
    total_path_loss_db=None,
):
    """Build the structured coverage report payload."""
    reliability = summarize_reliability(
        margin_db=max_prx_dbm - rx_sensitivity_dbm,
        frequency_mhz=f_mhz,
        distance_km=max_distance_km,
        los_blocked=False,
    )
    return {
        "report_type": "coverage",
        "generated_by": "NoWires",
        "inputs": {
            "tx_lat": round(tx_lat, 6),
            "tx_lon": round(tx_lon, 6),
            "tx_height_m": tx_h,
            "rx_height_m": rx_h,
            "frequency_mhz": f_mhz,
            "max_analysis_distance_km": radius_km,
            "grid_size": grid_size,
            "polarization": polarization_name,
            "climate": climate_name,
            "time_pct": time_pct,
            "location_pct": location_pct,
            "situation_pct": situation_pct,
            "tx_power_dbm": tx_power,
            "tx_gain_dbi": tx_gain,
            "rx_gain_dbi": rx_gain,
            "cable_loss_db": cable_loss,
            "rx_sensitivity_dbm": rx_sensitivity_dbm,
            "clutter_model": clutter_model,
            "clutter_source": clutter_source,
            "tx_antenna_preset": tx_antenna_preset,
        },
        "results": {
            "valid_pixel_count": valid_pixel_count,
            "pixel_count": pixel_count,
            "min_prx_dbm": min_prx_dbm,
            "max_prx_dbm": max_prx_dbm,
            "mean_prx_dbm": mean_prx_dbm,
            "pct_above_sensitivity": pct_above_sensitivity,
            "usable_cell_count": usable_cell_count,
            "itm_loss_db": itm_loss_db,
            "clutter_tx_db": clutter_tx_db,
            "clutter_rx_db": clutter_rx_db,
            "total_path_loss_db": total_path_loss_db,
            "availability_method": reliability["availability_method"],
            "availability_estimate_pct": reliability["availability_estimate_pct"],
            "fade_margin_class": reliability["fade_margin_class"],
            "reliability_summary": reliability["reliability_summary"],
            "min_distance_km": min_distance_km,
            "max_distance_km": max_distance_km,
            "average_distance_km": average_distance_km,
        },
        "status": {
            "summary": "HAS USABLE CELLS" if usable_cell_count else "NO USABLE CELLS",
            "usable_cells_present": bool(usable_cell_count),
        },
    }


def build_empty_coverage_report_payload(
    tx_lat,
    tx_lon,
    tx_h,
    rx_h,
    f_mhz,
    radius_km,
    grid_size,
    polarization_name,
    climate_name,
    time_pct,
    location_pct,
    situation_pct,
    tx_power,
    tx_gain,
    rx_gain,
    cable_loss,
    rx_sensitivity_dbm,
    pixel_count,
    clutter_model="Off",
    clutter_source="off",
    tx_antenna_preset="omni",
    itm_loss_db=None,
    clutter_tx_db=0.0,
    clutter_rx_db=0.0,
    total_path_loss_db=None,
):
    """Build a coverage report payload for a grid with no valid modelled cells."""
    reliability = summarize_reliability(
        margin_db=-999.0,
        frequency_mhz=f_mhz,
        distance_km=0.0,
        los_blocked=False,
    )
    return {
        "report_type": "coverage",
        "generated_by": "NoWires",
        "inputs": {
            "tx_lat": round(tx_lat, 6),
            "tx_lon": round(tx_lon, 6),
            "tx_height_m": tx_h,
            "rx_height_m": rx_h,
            "frequency_mhz": f_mhz,
            "max_analysis_distance_km": radius_km,
            "grid_size": grid_size,
            "polarization": polarization_name,
            "climate": climate_name,
            "time_pct": time_pct,
            "location_pct": location_pct,
            "situation_pct": situation_pct,
            "tx_power_dbm": tx_power,
            "tx_gain_dbi": tx_gain,
            "rx_gain_dbi": rx_gain,
            "cable_loss_db": cable_loss,
            "rx_sensitivity_dbm": rx_sensitivity_dbm,
            "clutter_model": clutter_model,
            "clutter_source": clutter_source,
            "tx_antenna_preset": tx_antenna_preset,
        },
        "results": {
            "valid_pixel_count": 0,
            "pixel_count": pixel_count,
            "min_prx_dbm": None,
            "max_prx_dbm": None,
            "mean_prx_dbm": None,
            "pct_above_sensitivity": 0.0,
            "usable_cell_count": 0,
            "itm_loss_db": itm_loss_db,
            "clutter_tx_db": clutter_tx_db,
            "clutter_rx_db": clutter_rx_db,
            "total_path_loss_db": total_path_loss_db,
            "availability_method": reliability["availability_method"],
            "availability_estimate_pct": reliability["availability_estimate_pct"],
            "fade_margin_class": reliability["fade_margin_class"],
            "reliability_summary": reliability["reliability_summary"],
            "min_distance_km": 0.0,
            "max_distance_km": 0.0,
            "average_distance_km": 0.0,
        },
        "status": {
            "summary": "NO VALID COVERAGE CELLS",
            "usable_cells_present": False,
        },
    }


def build_p2p_marker_records(
    tx_lat,
    tx_lon,
    rx_lat,
    rx_lon,
    tx_h,
    rx_h,
    tx_gain,
    rx_gain,
    tx_power_dbm,
    rx_sensitivity_dbm,
):
    """Return the TX/RX marker attribute rows."""
    return [
        {
            "role": "TX",
            "latitude": tx_lat,
            "longitude": tx_lon,
            "height_m": tx_h,
            "gain_dbi": tx_gain,
            "power_dbm": tx_power_dbm,
            "sensitivity_dbm": None,
        },
        {
            "role": "RX",
            "latitude": rx_lat,
            "longitude": rx_lon,
            "height_m": rx_h,
            "gain_dbi": rx_gain,
            "power_dbm": None,
            "sensitivity_dbm": rx_sensitivity_dbm,
        },
    ]


def write_p2p_marker_layer(
    path,
    tx_lat,
    tx_lon,
    rx_lat,
    rx_lon,
    tx_h,
    rx_h,
    tx_gain,
    rx_gain,
    tx_power_dbm,
    rx_sensitivity_dbm,
):
    """Write a TX/RX point layer to disk with OGR."""
    path = Path(path)
    driver = ogr.GetDriverByName(ogr_driver_for_path(path))
    _remove_existing_ogr_dataset(driver, path)

    ds = driver.CreateDataSource(str(path))
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

    layer = ds.CreateLayer("markers", srs=srs, geom_type=ogr.wkbPoint)
    layer.CreateField(ogr.FieldDefn("role", ogr.OFTString))
    layer.CreateField(ogr.FieldDefn("latitude", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("longitude", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("height_m", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("gain_dbi", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("power_dbm", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("sens_dbm", ogr.OFTReal))

    for row in build_p2p_marker_records(
        tx_lat=tx_lat,
        tx_lon=tx_lon,
        rx_lat=rx_lat,
        rx_lon=rx_lon,
        tx_h=tx_h,
        rx_h=rx_h,
        tx_gain=tx_gain,
        rx_gain=rx_gain,
        tx_power_dbm=tx_power_dbm,
        rx_sensitivity_dbm=rx_sensitivity_dbm,
    ):
        feature = ogr.Feature(layer.GetLayerDefn())
        geometry = ogr.Geometry(ogr.wkbPoint)
        geometry.AddPoint(row["longitude"], row["latitude"])
        feature.SetGeometry(geometry)
        feature.SetField("role", row["role"])
        feature.SetField("latitude", row["latitude"])
        feature.SetField("longitude", row["longitude"])
        feature.SetField("height_m", row["height_m"])
        feature.SetField("gain_dbi", row["gain_dbi"])
        if row["power_dbm"] is not None:
            feature.SetField("power_dbm", row["power_dbm"])
        if row["sensitivity_dbm"] is not None:
            feature.SetField("sens_dbm", row["sensitivity_dbm"])
        layer.CreateFeature(feature)

    ds = None
    return str(path)
