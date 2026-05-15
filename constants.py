# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
METERS_PER_DEGREE_LAT = 111320.0
DEGREE_PADDING = 0.05
DEFAULT_PROFILE_STEP_M = 30.0
FEET_PER_METER = 3.28084
BYTES_PER_MEBIBYTE = 1048576.0

POLARIZATION_NAMES = {0: "Horizontal", 1: "Vertical"}

CLIMATE_NAMES = {
    0: "Equatorial",
    1: "Continental Subtropical",
    2: "Maritime Subtropical",
    3: "Desert",
    4: "Continental Temperate",
    5: "Maritime Temperate (land)",
    6: "Maritime Temperate (sea)",
}

CLIMATE_OPTIONS = list(CLIMATE_NAMES.values())

GRID_SIZE_PRESETS = [64, 128, 192, 256, 384, 512, 768, 1024]

GRID_SIZE_OPTIONS = [
    "64 x 64", "128 x 128", "192 x 192", "256 x 256",
    "384 x 384", "512 x 512", "768 x 768", "1024 x 1024",
]

K_FACTOR_PRESETS_OPTIONS = [
    "0.67 - Sub-refractive",
    "1.00 - Geometric",
    "1.33 - Standard atmosphere",
    "2.00 - Super-refractive",
    "4.00 - Strong super-refractive",
    "Custom",
]

MAX_AOI_EXTENT_DEGREES = 5.0
EARTH_RADIUS_M = 6371000.0
COVERAGE_NODATA = -9999.0
ITM_LOSS_UPPER_BOUND = 400.0