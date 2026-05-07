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