# itm/__init__.py
"""
Pure-Python port of the ITS Irregular Terrain Model (ITM / Longley-Rice).

Predicts terrestrial radiowave propagation loss for frequencies 20 MHz – 20 GHz.
Public entry points: `predict_p2p` and `predict_area`.

Derived from tedaks/pyitm, a Python port of NTIA's Irregular Terrain Model.
Original work: Copyright NTIA and distributed under the NTIA Software
Disclaimer / Release. Local adaptations are limited to plugin packaging and
import-path adjustments. See NOTICE.md for attribution details.
"""

from .itm import predict_p2p, predict_area, predict_p2p_cr, predict_area_cr
from .models import (
    Climate,
    Polarization,
    MDVar,
    PropMode,
    SitingCriteria,
    TerrainProfile,
    IntermediateValues,
    PropagationResult,
    Warnings,
)

__version__ = "0.2.0"

__all__ = [
    "predict_p2p",
    "predict_area",
    "predict_p2p_cr",
    "predict_area_cr",
    "Climate",
    "Polarization",
    "MDVar",
    "PropMode",
    "SitingCriteria",
    "TerrainProfile",
    "IntermediateValues",
    "PropagationResult",
    "Warnings",
    "__version__",
]
