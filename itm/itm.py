# itm/itm.py
"""
Derived from tedaks/pyitm, a Python port of NTIA's Irregular Terrain Model.
Original work: Copyright NTIA and distributed under the NTIA Software
Disclaimer / Release. Local adaptations are limited to plugin packaging and
import-path adjustments. See NOTICE.md for attribution details.
"""

from __future__ import annotations
import logging
from ._constants import (
    WARN__TX_TERMINAL_HEIGHT,
    WARN__RX_TERMINAL_HEIGHT,
    WARN__FREQUENCY,
    MODE__P2P,
    MODE__AREA,
)
from .models import (
    Climate,
    Polarization,
    SitingCriteria,
    TerrainProfile,
    IntermediateValues,
    PropagationResult,
)
from .terrain import quick_pfl, initialize_area
from .propagation import initialize_point_to_point, longley_rice, free_space_loss
from .variability import variability

logger = logging.getLogger(__name__)


def _validate_inputs(
    h_tx__meter: float,
    h_rx__meter: float,
    climate: int,
    time: float,
    location: float,
    situation: float,
    N_0: float,
    f__mhz: float,
    pol: int,
    epsilon: float,
    sigma: float,
    mdvar: int,
) -> int:
    """Validate common inputs. Returns initial warnings bitmask. Raises ValueError on error.

    Check order matches the C++ ValidateInputs.cpp: warning-range checks before
    error-range checks so that the warning bitmask is populated even when an
    error will be raised.
    """
    warnings = 0

    # TX height: warn-range first, then error-range (matches C++ order)
    if h_tx__meter < 1.0 or h_tx__meter > 1000.0:
        warnings |= WARN__TX_TERMINAL_HEIGHT
    if h_tx__meter < 0.5 or h_tx__meter > 3000.0:
        raise ValueError(f"h_tx__meter={h_tx__meter} out of range [0.5, 3000]")

    # RX height: warn-range first, then error-range
    if h_rx__meter < 1.0 or h_rx__meter > 1000.0:
        warnings |= WARN__RX_TERMINAL_HEIGHT
    if h_rx__meter < 0.5 or h_rx__meter > 3000.0:
        raise ValueError(f"h_rx__meter={h_rx__meter} out of range [0.5, 3000]")

    valid_climates = {1, 2, 3, 4, 5, 6, 7}
    if int(climate) not in valid_climates:
        raise ValueError(f"climate={climate} is not a valid Climate value (1-7)")

    if N_0 < 250 or N_0 > 400:
        raise ValueError(f"N_0={N_0} out of range [250, 400]")

    # Frequency: warn-range first, then error-range
    if f__mhz < 40.0 or f__mhz > 10000.0:
        warnings |= WARN__FREQUENCY
    if f__mhz < 20 or f__mhz > 20000:
        raise ValueError(f"f__mhz={f__mhz} out of range [20, 20000]")

    if int(pol) not in (0, 1):
        raise ValueError(f"pol={pol} must be 0 (HORIZONTAL) or 1 (VERTICAL)")

    if epsilon < 1:
        raise ValueError(f"epsilon={epsilon} must be >= 1")

    if sigma <= 0:
        raise ValueError(f"sigma={sigma} must be > 0")

    valid_mdvar = (
        set(range(0, 4)) | set(range(10, 14)) | set(range(20, 24)) | set(range(30, 34))
    )
    if int(mdvar) not in valid_mdvar:
        raise ValueError(f"mdvar={mdvar} is not valid (0-3, 10-13, 20-23, 30-33)")

    if situation <= 0 or situation >= 100:
        raise ValueError(f"situation={situation} must be in (0, 100)")
    if time <= 0 or time >= 100:
        raise ValueError(f"time={time} must be in (0, 100)")
    if location <= 0 or location >= 100:
        raise ValueError(f"location={location} must be in (0, 100)")

    return warnings


def predict_p2p(
    h_tx__meter: float,
    h_rx__meter: float,
    terrain: TerrainProfile,
    climate: Climate,
    N_0: float,
    f__mhz: float,
    pol: Polarization,
    epsilon: float,
    sigma: float,
    mdvar: int,
    time: float,
    location: float,
    situation: float,
    *,
    return_intermediate: bool = False,
) -> PropagationResult:
    """Point-to-point propagation prediction.

    time, location, situation: percentages in (0, 100).
    mdvar: 0-3 base + optional +10 (no location var) and/or +20 (no situation var).
    """
    warnings = _validate_inputs(
        h_tx__meter,
        h_rx__meter,
        int(climate),
        time,
        location,
        situation,
        N_0,
        f__mhz,
        int(pol),
        epsilon,
        sigma,
        int(mdvar),
    )

    if len(terrain.elevations) < 2:
        raise ValueError(
            f"terrain must have at least 2 elevation points, got {len(terrain.elevations)}"
        )

    np_ = len(terrain.elevations) - 1
    p10 = int(0.1 * np_)
    h_sys__meter = float(terrain.elevations[p10 : np_ - p10 + 1].mean())

    Z_g, gamma_e, N_s = initialize_point_to_point(
        f__mhz, h_sys__meter, N_0, int(pol), epsilon, sigma
    )

    h__meter = (h_tx__meter, h_rx__meter)
    theta_hzn, d_hzn__meter, h_e__meter, delta_h__meter, d__meter = quick_pfl(
        terrain, gamma_e, h__meter
    )

    A_ref__db, lr_warnings, propmode = longley_rice(
        theta_hzn,
        f__mhz,
        Z_g,
        d_hzn__meter,
        h_e__meter,
        gamma_e,
        N_s,
        delta_h__meter,
        h__meter,
        d__meter,
        MODE__P2P,
    )
    warnings |= lr_warnings

    A_fs__db = free_space_loss(d__meter, f__mhz)

    var_db, var_warnings = variability(
        time,
        location,
        situation,
        h_e__meter,
        delta_h__meter,
        f__mhz,
        d__meter,
        A_ref__db,
        climate,
        int(mdvar),
    )
    warnings |= var_warnings

    A__db = var_db + A_fs__db

    inter = None
    if return_intermediate:
        inter = IntermediateValues(
            theta_hzn=(theta_hzn[0], theta_hzn[1]),
            d_hzn__meter=(d_hzn__meter[0], d_hzn__meter[1]),
            h_e__meter=(h_e__meter[0], h_e__meter[1]),
            N_s=N_s,
            delta_h__meter=delta_h__meter,
            A_ref__db=A_ref__db,
            A_fs__db=A_fs__db,
            d__km=d__meter / 1000.0,
            mode=propmode,
        )

    return PropagationResult(A__db=A__db, warnings=warnings, intermediate=inter)


def predict_area(
    h_tx__meter: float,
    h_rx__meter: float,
    tx_siting: SitingCriteria,
    rx_siting: SitingCriteria,
    d__km: float,
    delta_h__meter: float,
    climate: Climate,
    N_0: float,
    f__mhz: float,
    pol: Polarization,
    epsilon: float,
    sigma: float,
    mdvar: int,
    time: float,
    location: float,
    situation: float,
    *,
    return_intermediate: bool = False,
) -> PropagationResult:
    """Area-mode propagation prediction."""
    warnings = _validate_inputs(
        h_tx__meter,
        h_rx__meter,
        int(climate),
        time,
        location,
        situation,
        N_0,
        f__mhz,
        int(pol),
        epsilon,
        sigma,
        int(mdvar),
    )

    if d__km <= 0:
        raise ValueError(f"d__km={d__km} must be > 0")
    if delta_h__meter < 0:
        raise ValueError(f"delta_h__meter={delta_h__meter} must be >= 0")
    if int(tx_siting) not in (0, 1, 2):
        raise ValueError(f"tx_siting={tx_siting} is not a valid SitingCriteria")
    if int(rx_siting) not in (0, 1, 2):
        raise ValueError(f"rx_siting={rx_siting} is not a valid SitingCriteria")

    Z_g, gamma_e, N_s = initialize_point_to_point(
        f__mhz, 0.0, N_0, int(pol), epsilon, sigma
    )

    h__meter = (h_tx__meter, h_rx__meter)
    site_criteria = (int(tx_siting), int(rx_siting))
    h_e__meter, d_hzn__meter, theta_hzn = initialize_area(
        site_criteria, gamma_e, delta_h__meter, h__meter
    )

    d__meter = d__km * 1000.0
    A_ref__db, lr_warnings, propmode = longley_rice(
        theta_hzn,
        f__mhz,
        Z_g,
        d_hzn__meter,
        h_e__meter,
        gamma_e,
        N_s,
        delta_h__meter,
        h__meter,
        d__meter,
        MODE__AREA,
    )
    warnings |= lr_warnings

    A_fs__db = free_space_loss(d__meter, f__mhz)

    var_db, var_warnings = variability(
        time,
        location,
        situation,
        h_e__meter,
        delta_h__meter,
        f__mhz,
        d__meter,
        A_ref__db,
        climate,
        int(mdvar),
    )
    warnings |= var_warnings

    A__db = A_fs__db + var_db

    inter = None
    if return_intermediate:
        inter = IntermediateValues(
            theta_hzn=(theta_hzn[0], theta_hzn[1]),
            d_hzn__meter=(d_hzn__meter[0], d_hzn__meter[1]),
            h_e__meter=(h_e__meter[0], h_e__meter[1]),
            N_s=N_s,
            delta_h__meter=delta_h__meter,
            A_ref__db=A_ref__db,
            A_fs__db=A_fs__db,
            d__km=d__km,
            mode=propmode,
        )

    return PropagationResult(A__db=A__db, warnings=warnings, intermediate=inter)


def predict_p2p_cr(
    h_tx__meter: float,
    h_rx__meter: float,
    terrain: TerrainProfile,
    climate: Climate,
    N_0: float,
    f__mhz: float,
    pol: Polarization,
    epsilon: float,
    sigma: float,
    mdvar: int,
    confidence: float,
    reliability: float,
    *,
    return_intermediate: bool = False,
) -> PropagationResult:
    """Point-to-point propagation with confidence/reliability (CR) mode.

    confidence, reliability: percentages in (0, 100).
    mdvar: mode of variability (0-3, 10-13, 20-23, 30-33).
    Internally maps to TLS as: time=reliability, location=50, situation=confidence.
    This matches the C++ ITM_P2P_CR_Ex mapping.
    """
    return predict_p2p(
        h_tx__meter=h_tx__meter,
        h_rx__meter=h_rx__meter,
        terrain=terrain,
        climate=climate,
        N_0=N_0,
        f__mhz=f__mhz,
        pol=pol,
        epsilon=epsilon,
        sigma=sigma,
        mdvar=mdvar,
        time=reliability,
        location=50.0,
        situation=confidence,
        return_intermediate=return_intermediate,
    )


def predict_area_cr(
    h_tx__meter: float,
    h_rx__meter: float,
    tx_siting: SitingCriteria,
    rx_siting: SitingCriteria,
    d__km: float,
    delta_h__meter: float,
    climate: Climate,
    N_0: float,
    f__mhz: float,
    pol: Polarization,
    epsilon: float,
    sigma: float,
    mdvar: int,
    confidence: float,
    reliability: float,
    *,
    return_intermediate: bool = False,
) -> PropagationResult:
    """Area-mode propagation with confidence/reliability (CR) mode.

    confidence, reliability: percentages in (0, 100).
    mdvar: mode of variability (0-3, 10-13, 20-23, 30-33).
    Internally maps to TLS as: time=reliability, location=50, situation=confidence.
    This matches the C++ ITM_AREA_CR_Ex mapping.
    """
    return predict_area(
        h_tx__meter=h_tx__meter,
        h_rx__meter=h_rx__meter,
        tx_siting=tx_siting,
        rx_siting=rx_siting,
        d__km=d__km,
        delta_h__meter=delta_h__meter,
        climate=climate,
        N_0=N_0,
        f__mhz=f__mhz,
        pol=pol,
        epsilon=epsilon,
        sigma=sigma,
        mdvar=mdvar,
        time=reliability,
        location=50.0,
        situation=confidence,
        return_intermediate=return_intermediate,
    )
