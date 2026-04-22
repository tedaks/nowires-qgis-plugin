# itm/propagation.py
"""
Derived from tedaks/pyitm, a Python port of NTIA's Irregular Terrain Model.
Original work: Copyright NTIA and distributed under the NTIA Software
Disclaimer / Release. Local adaptations are limited to plugin packaging and
import-path adjustments. See NOTICE.md for attribution details.
"""

from __future__ import annotations
import math
import cmath
from ._constants import (
    PI,
    SQRT2,
    THIRD,
    a_0__meter,
    WN_DENOM,
    GAMMA_A,
    Z_0__meter,
    Z_1__meter,
    D_0__meter,
    TROPO_H__meter,
    WARN__TX_HORIZON_ANGLE,
    WARN__RX_HORIZON_ANGLE,
    WARN__TX_HORIZON_DISTANCE_1,
    WARN__RX_HORIZON_DISTANCE_1,
    WARN__TX_HORIZON_DISTANCE_2,
    WARN__RX_HORIZON_DISTANCE_2,
    WARN__PATH_DISTANCE_TOO_SMALL_1,
    WARN__PATH_DISTANCE_TOO_SMALL_2,
    WARN__PATH_DISTANCE_TOO_BIG_1,
    WARN__PATH_DISTANCE_TOO_BIG_2,
    WARN__SURFACE_REFRACTIVITY,
    MODE__P2P,
)
from .models import PropMode
from .variability import terrain_roughness, sigma_h_function


def free_space_loss(d__meter: float, f__mhz: float) -> float:
    """Free space basic transmission loss. [Algorithm]"""
    return 32.45 + 20.0 * math.log10(f__mhz) + 20.0 * math.log10(d__meter / 1000.0)


def fresnel_integral(v2: float) -> float:
    """Approximate knife-edge diffraction loss. v2 is v^2. [TN101v2, Eqn III.24]"""
    if v2 < 5.76:
        return 6.02 + 9.11 * math.sqrt(v2) - 1.27 * v2
    else:
        return 12.953 + 10.0 * math.log10(v2)


def knife_edge_diffraction(
    d__meter: float,
    f__mhz: float,
    a_e__meter: float,
    theta_los: float,
    d_hzn__meter: list[float],
) -> float:
    """Knife-edge diffraction loss. [TN101, Eqn I.7 & I.1]"""
    d_ML__meter = d_hzn__meter[0] + d_hzn__meter[1]
    theta_nlos = d__meter / a_e__meter - theta_los
    d_nlos__meter = d__meter - d_ML__meter

    v_1 = (
        0.0795775
        * (f__mhz / WN_DENOM)
        * theta_nlos**2
        * d_hzn__meter[0]
        * d_nlos__meter
        / (d_nlos__meter + d_hzn__meter[0])
    )
    v_2 = (
        0.0795775
        * (f__mhz / WN_DENOM)
        * theta_nlos**2
        * d_hzn__meter[1]
        * d_nlos__meter
        / (d_nlos__meter + d_hzn__meter[1])
    )

    return fresnel_integral(v_1) + fresnel_integral(v_2)


def height_function(x__km: float, K: float) -> float:
    """Height gain function F(x, K) for smooth earth diffraction. [Vogler 1964]"""
    if x__km < 200.0:
        w = -math.log(K)
        if K < 1e-5 or x__km * w**3 > 5495.0:
            result = -117.0
            if x__km > 1.0:
                result = 17.372 * math.log(x__km) + result
        else:
            result = 2.5e-5 * x__km**2 / K - 8.686 * w - 15.0
    else:
        result = 0.05751 * x__km - 4.343 * math.log(x__km)
        if x__km < 2000.0:
            w = 0.0134 * x__km * math.exp(-0.005 * x__km)
            result = (1.0 - w) * result + w * (17.372 * math.log(x__km) - 117.0)
    return result


def smooth_earth_diffraction(
    d__meter: float,
    f__mhz: float,
    a_e__meter: float,
    theta_los: float,
    d_hzn__meter: list[float],
    h_e__meter: list[float],
    Z_g: complex,
) -> float:
    """Smooth earth diffraction loss using the Vogler 3-radii method. [Vogler 1964]

    Preconditions: h_e__meter[i] > 0; (d__meter / a_e__meter - theta_los) > 0.
    Both are guaranteed when called from longley_rice with d >= d_ML.
    """
    theta_nlos = d__meter / a_e__meter - theta_los
    d_ML__meter = d_hzn__meter[0] + d_hzn__meter[1]

    # 3 radii [Vogler 1964, Eqn 3 re-arranged]
    a__meter = [
        (d__meter - d_ML__meter) / (d__meter / a_e__meter - theta_los),
        0.5 * d_hzn__meter[0] ** 2 / h_e__meter[0],
        0.5 * d_hzn__meter[1] ** 2 / h_e__meter[1],
    ]
    d__km_vogler = [
        a__meter[0] * theta_nlos / 1000.0,
        d_hzn__meter[0] / 1000.0,
        d_hzn__meter[1] / 1000.0,
    ]

    C_0 = [pow((4.0 / 3.0) * a_0__meter / a__meter[i], THIRD) for i in range(3)]
    # [Vogler 1964, Eqn 6a / 7a]
    K = [0.017778 * C_0[i] * pow(f__mhz, -THIRD) / abs(Z_g) for i in range(3)]
    B_0 = [1.607 - K[i] for i in range(3)]

    x__km = [0.0, 0.0, 0.0]
    x__km[1] = B_0[1] * C_0[1] ** 2 * f__mhz**THIRD * d__km_vogler[1]
    x__km[2] = B_0[2] * C_0[2] ** 2 * f__mhz**THIRD * d__km_vogler[2]
    x__km[0] = (
        B_0[0] * C_0[0] ** 2 * f__mhz**THIRD * d__km_vogler[0] + x__km[1] + x__km[2]
    )

    F_x = [height_function(x__km[1], K[1]), height_function(x__km[2], K[2])]

    G_x__db = 0.05751 * x__km[0] - 10.0 * math.log10(x__km[0])

    return G_x__db - F_x[0] - F_x[1] - 20.0


def h0_curve(j: int, r: float) -> float:
    """Curve fit helper for H_0(). [Algorithm, 6.13]"""
    a = [25.0, 80.0, 177.0, 395.0, 705.0]
    b = [24.0, 45.0, 68.0, 80.0, 105.0]
    return 10.0 * math.log10(1.0 + a[j] * (1.0 / r) ** 4 + b[j] * (1.0 / r) ** 2)


def h0_function(r: float, eta_s: float) -> float:
    """Troposcatter frequency gain H_0(). [TN101v1, Ch 9.2]"""
    eta_s = min(max(eta_s, 1.0), 5.0)
    i = int(eta_s)
    q = eta_s - i
    result = h0_curve(i - 1, r)
    if q != 0.0:
        result = (1.0 - q) * result + q * h0_curve(i, r)
    return result


def f_function(td: float) -> float:
    """Attenuation function F(theta*d). [Algorithm, 6.9]"""
    a = [133.4, 104.6, 71.8]
    b = [0.332e-3, 0.212e-3, 0.157e-3]
    c = [-10.0, -2.5, 5.0]
    if td <= 10e3:
        i = 0
    elif td <= 70e3:
        i = 1
    else:
        i = 2
    return a[i] + b[i] * td + c[i] * math.log10(td)


def troposcatter_loss(
    d__meter: float,
    theta_hzn: list[float],
    d_hzn__meter: list[float],
    h_e__meter: list[float],
    a_e__meter: float,
    N_s: float,
    f__mhz: float,
    theta_los: float,
    h0: float,
) -> tuple[float, float]:
    """Compute troposcatter loss and updated h0 value.

    Returns (A_scat__db, h0_updated).
    Returns (1001.0, h0) when path geometry makes troposcatter undefined.
    Precondition: h_e__meter[0] > 0 (division by h_e__meter[0] on line ~194).
    Guaranteed by public API validation (h_tx__meter >= 0.5).
    """
    wn = f__mhz / WN_DENOM

    if h0 > 15.0:
        H_0 = h0
    else:
        ad = d_hzn__meter[0] - d_hzn__meter[1]
        rr = h_e__meter[1] / h_e__meter[0]

        if ad < 0.0:
            ad = -ad
            rr = 1.0 / rr

        theta = theta_hzn[0] + theta_hzn[1] + d__meter / a_e__meter

        r_1 = 2.0 * wn * theta * h_e__meter[0]
        r_2 = 2.0 * wn * theta * h_e__meter[1]

        if r_1 < 0.2 and r_2 < 0.2:
            return 1001.0, h0

        s = (d__meter - ad) / (d__meter + ad)
        q = min(max(0.1, rr / s), 10.0)
        s = max(0.1, s)

        h_0__meter = (d__meter - ad) * (d__meter + ad) * theta * 0.25 / d__meter

        eta_s = (h_0__meter / Z_0__meter) * (
            1.0
            + (0.031 - N_s * 2.32e-3 + N_s**2 * 5.67e-6)
            * math.exp(-pow(min(1.7, h_0__meter / Z_1__meter), 6))
        )

        H_00 = (h0_function(r_1, eta_s) + h0_function(r_2, eta_s)) / 2.0
        Delta_H_0 = min(
            H_00,
            6.0 * (0.6 - math.log10(max(eta_s, 1.0))) * math.log10(s) * math.log10(q),
        )

        H_0 = max(H_00 + Delta_H_0, 0.0)

        if eta_s < 1.0:
            H_0 = eta_s * H_0 + (1.0 - eta_s) * 10.0 * math.log10(
                ((1.0 + SQRT2 / r_1) * (1.0 + SQRT2 / r_2)) ** 2
                * (r_1 + r_2)
                / (r_1 + r_2 + 2.0 * SQRT2)
            )

        if H_0 > 15.0 and h0 >= 0.0:
            H_0 = h0

    h0_updated = H_0
    th = d__meter / a_e__meter - theta_los

    result = (
        f_function(th * d__meter)
        + 10.0 * math.log10(wn * TROPO_H__meter * th**4)
        - 0.1 * (N_s - 301.0) * math.exp(-th * d__meter / D_0__meter)
        + H_0
    )
    return result, h0_updated


def line_of_sight_loss(
    d__meter: float,
    h_e__meter: list[float],
    Z_g: complex,
    delta_h__meter: float,
    M_d: float,
    A_d0: float,
    d_sML__meter: float,
    f__mhz: float,
) -> float:
    """Loss in the line-of-sight region. [Algorithm, Eqn 4.46-4.50]"""
    delta_h_d__meter = terrain_roughness(d__meter, delta_h__meter)
    sigma_h_d__meter = sigma_h_function(delta_h_d__meter)

    wn = f__mhz / WN_DENOM

    sin_psi = (h_e__meter[0] + h_e__meter[1]) / math.sqrt(
        d__meter**2 + (h_e__meter[0] + h_e__meter[1]) ** 2
    )

    R_e = (
        (sin_psi - Z_g)
        / (sin_psi + Z_g)
        * math.exp(-min(10.0, wn * sigma_h_d__meter * sin_psi))
    )

    q = R_e.real**2 + R_e.imag**2
    if q < 0.25 or q < sin_psi:
        R_e = R_e * math.sqrt(sin_psi / q)

    delta_phi = wn * 2.0 * h_e__meter[0] * h_e__meter[1] / d__meter
    if delta_phi > PI / 2.0:
        delta_phi = PI - (PI / 2.0) ** 2 / delta_phi

    rr = complex(math.cos(delta_phi), -math.sin(delta_phi)) + R_e
    A_t__db = -10.0 * math.log10(rr.real**2 + rr.imag**2)

    A_d__db = M_d * d__meter + A_d0
    w = 1.0 / (1.0 + f__mhz * delta_h__meter / max(10e3, d_sML__meter))

    return w * A_t__db + (1.0 - w) * A_d__db


def diffraction_loss(
    d__meter: float,
    d_hzn__meter: list[float],
    h_e__meter: list[float],
    Z_g: complex,
    a_e__meter: float,
    delta_h__meter: float,
    h__meter: tuple[float, float],
    mode: int,
    theta_los: float,
    d_sML__meter: float,
    f__mhz: float,
) -> float:
    """Combined diffraction loss (knife-edge + smooth earth + terrain clutter).

    [ERL 79-ITS 67, Eqn 3.23 & 3.38c]
    """
    A_k__db = knife_edge_diffraction(
        d__meter, f__mhz, a_e__meter, theta_los, d_hzn__meter
    )
    A_se__db = smooth_earth_diffraction(
        d__meter, f__mhz, a_e__meter, theta_los, d_hzn__meter, h_e__meter, Z_g
    )

    delta_h_dsML__meter = terrain_roughness(d_sML__meter, delta_h__meter)
    sigma_h_d__meter = sigma_h_function(delta_h_dsML__meter)

    # Clutter factor [ERL 79-ITS 67, Eqn 3.38c]
    A_fo__db = min(
        15.0,
        5.0
        * math.log10(
            1.0 + 1e-5 * h__meter[0] * h__meter[1] * f__mhz * sigma_h_d__meter
        ),
    )

    delta_h_d__meter = terrain_roughness(d__meter, delta_h__meter)
    q = h__meter[0] * h__meter[1]
    qk = h_e__meter[0] * h_e__meter[1] - q

    if mode == MODE__P2P:
        q += 10.0  # C ≈ 10 for low antennas with known path [ERL 79-ITS 67, page 3-8]

    term1 = math.sqrt(1.0 + qk / q)
    d_ML__meter = d_hzn__meter[0] + d_hzn__meter[1]
    q = (term1 + (-theta_los * a_e__meter + d_ML__meter) / d__meter) * min(
        delta_h_d__meter * f__mhz / WN_DENOM, 6283.2
    )
    w = 25.1 / (25.1 + math.sqrt(q))

    return w * A_se__db + (1.0 - w) * A_k__db + A_fo__db


def initialize_point_to_point(
    f__mhz: float,
    h_sys__meter: float,
    N_0: float,
    pol: int,
    epsilon: float,
    sigma: float,
) -> tuple[complex, float, float]:
    """Compute ground impedance, effective earth curvature, surface refractivity.

    Returns (Z_g, gamma_e, N_s).
    """
    if h_sys__meter == 0.0:
        N_s = N_0
    else:
        N_s = N_0 * math.exp(-h_sys__meter / 9460.0)  # [TN101, Eq 4.3]

    gamma_e = GAMMA_A * (
        1.0 - 0.04665 * math.exp(N_s / 179.3)
    )  # [TN101, Eq 4.4] reworked

    ep_r = complex(epsilon, 18000.0 * sigma / f__mhz)
    Z_g = cmath.sqrt(ep_r - 1.0)

    if pol == 1:  # VERTICAL
        Z_g = Z_g / ep_r

    return Z_g, gamma_e, N_s


def longley_rice(
    theta_hzn: list[float],
    f__mhz: float,
    Z_g: complex,
    d_hzn__meter: list[float],
    h_e__meter: list[float],
    gamma_e: float,
    N_s: float,
    delta_h__meter: float,
    h__meter: tuple[float, float],
    d__meter: float,
    mode: int,
) -> tuple[float, int, PropMode]:
    """Core Longley-Rice reference attenuation computation.

    Returns (A_ref__db, warnings_bits, propmode).
    Raises ValueError for invalid computed parameters (surface refractivity,
    effective earth radius, ground impedance).
    """
    warnings = 0
    a_e__meter = 1.0 / gamma_e

    d_hzn_s__meter = [math.sqrt(2.0 * h_e__meter[i] * a_e__meter) for i in range(2)]
    d_sML__meter = d_hzn_s__meter[0] + d_hzn_s__meter[1]
    d_ML__meter = d_hzn__meter[0] + d_hzn__meter[1]

    theta_los = -max(theta_hzn[0] + theta_hzn[1], -d_ML__meter / a_e__meter)

    # Horizon angle warnings
    if math.fabs(theta_hzn[0]) > 200e-3:
        warnings |= WARN__TX_HORIZON_ANGLE
    if math.fabs(theta_hzn[1]) > 200e-3:
        warnings |= WARN__RX_HORIZON_ANGLE

    # Horizon distance warnings
    if d_hzn__meter[0] < 0.1 * d_hzn_s__meter[0]:
        warnings |= WARN__TX_HORIZON_DISTANCE_1
    if d_hzn__meter[1] < 0.1 * d_hzn_s__meter[1]:
        warnings |= WARN__RX_HORIZON_DISTANCE_1
    if d_hzn__meter[0] > 3.0 * d_hzn_s__meter[0]:
        warnings |= WARN__TX_HORIZON_DISTANCE_2
    if d_hzn__meter[1] > 3.0 * d_hzn_s__meter[1]:
        warnings |= WARN__RX_HORIZON_DISTANCE_2

    if N_s < 150:
        raise ValueError(f"Surface refractivity N_s={N_s:.1f} is too small (< 150)")
    if N_s > 400:
        raise ValueError(f"Surface refractivity N_s={N_s:.1f} is too large (> 400)")
    if N_s < 250:
        warnings |= WARN__SURFACE_REFRACTIVITY

    if a_e__meter < 4_000_000 or a_e__meter > 13_333_333:
        raise ValueError(
            f"Effective earth radius a_e={a_e__meter:.0f} m is out of range"
        )

    if Z_g.real <= abs(Z_g.imag):
        raise ValueError(
            "Ground impedance: real part must exceed imaginary part magnitude"
        )

    # Two reference distances in the diffraction region
    d_diff_step = 10.0 * pow(a_e__meter**2 / f__mhz, 1.0 / 3.0)
    d_3__meter = max(d_sML__meter, d_ML__meter + 0.5 * d_diff_step)
    d_4__meter = d_3__meter + d_diff_step

    A_3__db = diffraction_loss(
        d_3__meter,
        d_hzn__meter,
        h_e__meter,
        Z_g,
        a_e__meter,
        delta_h__meter,
        h__meter,
        mode,
        theta_los,
        d_sML__meter,
        f__mhz,
    )
    A_4__db = diffraction_loss(
        d_4__meter,
        d_hzn__meter,
        h_e__meter,
        Z_g,
        a_e__meter,
        delta_h__meter,
        h__meter,
        mode,
        theta_los,
        d_sML__meter,
        f__mhz,
    )

    M_d = (A_4__db - A_3__db) / (d_4__meter - d_3__meter)
    A_d0__db = A_3__db - M_d * d_3__meter

    d_min__meter = math.fabs(h_e__meter[0] - h_e__meter[1]) / 200e-3

    if d__meter < d_min__meter:
        warnings |= WARN__PATH_DISTANCE_TOO_SMALL_1
    if d__meter < 1e3:
        warnings |= WARN__PATH_DISTANCE_TOO_SMALL_2
    if d__meter > 1000e3:
        warnings |= WARN__PATH_DISTANCE_TOO_BIG_1
    if d__meter > 2000e3:
        warnings |= WARN__PATH_DISTANCE_TOO_BIG_2

    if d__meter < d_sML__meter:
        # Line-of-sight path
        A_sML__db = d_sML__meter * M_d + A_d0__db
        d_0__meter = 0.04 * f__mhz * h_e__meter[0] * h_e__meter[1]

        if A_d0__db >= 0.0:
            d_0__meter = min(d_0__meter, 0.5 * d_ML__meter)
            d_1__meter = d_0__meter + 0.25 * (d_ML__meter - d_0__meter)
        else:
            d_1__meter = max(-A_d0__db / M_d, 0.25 * d_ML__meter)

        A_1__db = line_of_sight_loss(
            d_1__meter,
            h_e__meter,
            Z_g,
            delta_h__meter,
            M_d,
            A_d0__db,
            d_sML__meter,
            f__mhz,
        )

        flag = False
        kHat_1 = 0.0
        kHat_2 = 0.0

        if d_0__meter < d_1__meter:
            A_0__db = line_of_sight_loss(
                d_0__meter,
                h_e__meter,
                Z_g,
                delta_h__meter,
                M_d,
                A_d0__db,
                d_sML__meter,
                f__mhz,
            )
            q = math.log(d_sML__meter / d_0__meter)
            kHat_2 = max(
                0.0,
                (
                    (d_sML__meter - d_0__meter) * (A_1__db - A_0__db)
                    - (d_1__meter - d_0__meter) * (A_sML__db - A_0__db)
                )
                / (
                    (d_sML__meter - d_0__meter) * math.log(d_1__meter / d_0__meter)
                    - (d_1__meter - d_0__meter) * q
                ),
            )
            flag = A_d0__db > 0.0 or kHat_2 > 0.0

            if flag:
                kHat_1 = (A_sML__db - A_0__db - kHat_2 * q) / (
                    d_sML__meter - d_0__meter
                )
                if kHat_1 < 0.0:
                    kHat_1 = 0.0
                    kHat_2 = max(A_sML__db - A_0__db, 0.0) / q
                    if kHat_2 == 0.0:
                        kHat_1 = M_d

        if not flag:
            kHat_1 = max(A_sML__db - A_1__db, 0.0) / (d_sML__meter - d_1__meter)
            kHat_2 = 0.0
            if kHat_1 == 0.0:
                kHat_1 = M_d

        A_o__db = A_sML__db - kHat_1 * d_sML__meter - kHat_2 * math.log(d_sML__meter)
        A_ref__db = A_o__db + kHat_1 * d__meter + kHat_2 * math.log(d__meter)
        propmode = PropMode.LINE_OF_SIGHT
    else:
        # Trans-horizon path
        d_5__meter = d_ML__meter + 200e3
        d_6__meter = d_ML__meter + 400e3

        h0 = -1.0
        A_6__db, h0 = troposcatter_loss(
            d_6__meter,
            theta_hzn,
            d_hzn__meter,
            h_e__meter,
            a_e__meter,
            N_s,
            f__mhz,
            theta_los,
            h0,
        )
        A_5__db, h0 = troposcatter_loss(
            d_5__meter,
            theta_hzn,
            d_hzn__meter,
            h_e__meter,
            a_e__meter,
            N_s,
            f__mhz,
            theta_los,
            h0,
        )

        if A_5__db < 1000.0:
            M_s = (A_6__db - A_5__db) / 200e3
            d_x__meter = max(
                max(
                    d_sML__meter,
                    d_ML__meter
                    + 1.088 * pow(a_e__meter**2 / f__mhz, 1.0 / 3.0) * math.log(f__mhz),
                ),
                (A_5__db - A_d0__db - M_s * d_5__meter) / (M_d - M_s),
            )
            A_s0__db = (M_d - M_s) * d_x__meter + A_d0__db
        else:
            M_s = M_d
            A_s0__db = A_d0__db
            d_x__meter = 10e6

        if d__meter > d_x__meter:
            A_ref__db = M_s * d__meter + A_s0__db
            propmode = PropMode.TROPOSCATTER
        else:
            A_ref__db = M_d * d__meter + A_d0__db
            propmode = PropMode.DIFFRACTION

    A_ref__db = max(A_ref__db, 0.0)
    return A_ref__db, warnings, propmode
