from dataclasses import dataclass


@dataclass(frozen=True)
class ClutterLossContext:
    frequency_mhz: float
    distance_m: float
    tx_height_m: float
    rx_height_m: float
    rx_ground_elevation_m: float = 0.0
    polarization: int = 0
    cch_override_m: float | None = None
    model: str = "simple"
    percentile: float = 50.0
    street_width_m: float = 27.0
    bel_enabled: bool = False
    bel_building_type: str = "traditional"
    bel_elevation_angle_deg: float = 0.0