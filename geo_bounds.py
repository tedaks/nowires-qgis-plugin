"""Geographic bounding-box helpers for longitude wraparound."""


def normalize_longitude(lon):
    """Return longitude normalized to [-180, 180)."""
    return ((float(lon) + 180.0) % 360.0) - 180.0


def longitude_intervals(west, east):
    """Split a longitude span into one or two non-wrapping intervals."""
    west = normalize_longitude(west)
    east = normalize_longitude(east)
    if west <= east:
        return [(west, east)]
    return [(west, 180.0), (-180.0, east)]


def shortest_longitude_bounds(lon_a, lon_b, padding_deg=0.0):
    """Return the shortest west/east bounds covering two longitudes.

    A returned ``west > east`` pair means the interval crosses the antimeridian.
    """
    return shortest_longitude_bounds_for([lon_a, lon_b], padding_deg=padding_deg)


def shortest_longitude_bounds_for(longitudes, padding_deg=0.0):
    """Return the shortest west/east bounds covering all longitudes."""
    values = [float(lon) % 360.0 for lon in longitudes]
    if not values:
        return -180.0, 180.0
    values = sorted(values)
    if len(values) == 1:
        west = values[0] - padding_deg
        east = values[0] + padding_deg
        return normalize_longitude(west), normalize_longitude(east)

    gaps = []
    for idx, value in enumerate(values):
        next_value = values[(idx + 1) % len(values)]
        if idx == len(values) - 1:
            next_value += 360.0
        gaps.append((next_value - value, idx))

    largest_gap, gap_idx = max(gaps)
    covered_span = 360.0 - largest_gap + (2.0 * padding_deg)
    if covered_span >= 360.0:
        return -180.0, 180.0

    start = values[(gap_idx + 1) % len(values)] - padding_deg
    end = values[gap_idx] + padding_deg
    if end < start:
        end += 360.0
    return normalize_longitude(start), normalize_longitude(end)
