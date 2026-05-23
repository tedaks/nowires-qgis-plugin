# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import math
import os
import xml.etree.ElementTree as ET  # nosec B405

import numpy as np
from osgeo import gdal

from NoWires.constants import DEM_NODATA

try:
    from defusedxml.ElementTree import parse as _safe_parse  # nosec B405
    _XML_SAFE = True
except ImportError:
    _safe_parse = None  # type: ignore[assignment]  # fallback when defusedxml not installed
    _XML_SAFE = False

def _parse_xml(path):  # explicit call avoids a global ET.parse monkey-patch
    return _safe_parse(path) if _safe_parse is not None else ET.parse(path)  # nosec B314

logger = logging.getLogger(__name__)

def _raster_calc(calc_func, output_path, nodata=DEM_NODATA, overwrite=False, **inputs):
    arrays = {}
    datasets = []
    geo_transform = None
    projection = None
    rows = cols = 0
    out_ds = None
    try:
        for name, path in inputs.items():
            ds = gdal.Open(path)
            if ds is None:
                raise RuntimeError("Cannot open raster: " + str(path))
            datasets.append(ds)
            band = ds.GetRasterBand(1)
            if geo_transform is None:
                geo_transform = ds.GetGeoTransform()
                projection = ds.GetProjection()
                rows = ds.RasterYSize
                cols = ds.RasterXSize
            arr = band.ReadAsArray().astype(np.float32)
            input_nodata = band.GetNoDataValue()
            if input_nodata is not None:
                arr[arr == input_nodata] = np.nan
            arrays[name] = arr
        result = calc_func(**arrays)
        result[np.isnan(result)] = nodata
        if not overwrite and os.path.exists(output_path):
            raise RuntimeError("Output file already exists: " + output_path)
        driver = gdal.GetDriverByName("GTiff")
        out_ds = driver.Create(output_path, cols, rows, 1, gdal.GDT_Float32)
        out_ds.SetGeoTransform(geo_transform)
        out_ds.SetProjection(projection)
        out_band = out_ds.GetRasterBand(1)
        out_band.SetNoDataValue(nodata)
        out_band.WriteArray(result)
        out_band.FlushCache()
        out_band = None
        out_ds = None
    finally:
        out_ds = None
        while datasets:
            ds = datasets.pop()
            ds = None

def _gaussian_kernel_2d(size, sigma=None):
    """Generate a normalised 2D Gaussian kernel as a flat string of coefficients.

    The kernel is centred at the middle pixel. If *sigma* is ``None`` it
    defaults to ``size / 6.0`` so that the kernel covers ±3σ (the standard
    "3-sigma rule" for a Gaussian), matching the visual appearance of the
    original hand-tuned kernels.

    Returns a space-separated string with exactly ``size * size`` coefficients,
    suitable for embedding in a GDAL VRT ``<Coefs>`` element.
    """
    if sigma is None:
        sigma = size / 6.0
    centre = size // 2
    coeffs = []
    for y in range(size):
        for x in range(size):
            dx = x - centre
            dy = y - centre
            val = math.exp(-(dx * dx + dy * dy) / (2.0 * sigma * sigma))
            coeffs.append(val)
    total = sum(coeffs)
    return " ".join("{:.6f}".format(c / total) for c in coeffs)

def _make_blur_vrt(vrt_path, src_path, kernel_size, sigma=None):
    """Build a VRT that applies a Gaussian blur of *kernel_size* × *kernel_size*.

    Creates the VRT from the source raster, then patches it to use GDAL's
    ``KernelFilteredSource`` with the generated Gaussian coefficients.
    """
    gdal.BuildVRT(vrt_path, src_path)
    tree = _parse_xml(vrt_path)
    root = tree.getroot()
    ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""

    for source_elem in list(root.iter()):
        if source_elem.tag not in (
            "{}SimpleSource".format(ns),
            "{}ComplexSource".format(ns),
        ):
            continue
        source_elem.tag = "{}KernelFilteredSource".format(ns)
        kernel_elem = ET.SubElement(source_elem, "{}Kernel".format(ns))
        kernel_elem.set("normalized", "1")
        size_elem = ET.SubElement(kernel_elem, "{}Size".format(ns))
        size_elem.text = str(kernel_size)
        coefs_elem = ET.SubElement(kernel_elem, "{}Coefs".format(ns))
        coefs_elem.text = _gaussian_kernel_2d(kernel_size, sigma)

    tree.write(vrt_path, xml_declaration=True, encoding="utf-8")
