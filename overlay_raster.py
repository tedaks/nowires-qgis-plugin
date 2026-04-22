# -*- coding: utf-8 -*-
"""Helpers for preparing lightweight rasters used only for map overlays."""


DEFAULT_OVERLAY_MAX_DIMENSION = 2048


def choose_overlay_dimensions(width, height, max_dimension=DEFAULT_OVERLAY_MAX_DIMENSION):
    """Return a capped raster size for fast display while preserving aspect ratio."""
    longest_side = max(width, height)
    if longest_side <= max_dimension:
        return (int(width), int(height), 1.0)

    scale = float(max_dimension) / float(longest_side)
    scaled_width = max(1, int(round(width * scale)))
    scaled_height = max(1, int(round(height * scale)))
    return (scaled_width, scaled_height, scale)


def build_overview_levels(width, height, minimum_dimension=256):
    """Return power-of-two overview levels until the raster becomes small enough."""
    longest_side = max(width, height)
    levels = []
    level = 2
    while longest_side / level >= minimum_dimension:
        levels.append(level)
        level *= 2
    return levels
