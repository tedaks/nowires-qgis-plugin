# -*- coding: utf-8 -*-
"""
Numba-accelerated ITM computation for coverage analysis.

Provides a fused nopython entry point that computes ITM p2p loss
from raw terrain arrays without Python object overhead.

If numba is unavailable, falls back to the pure-Python path.
"""

import math

try:
    from numba import njit as _njit

    _HAS_NUMBA = True
except ImportError:
    _HAS_NUMBA = False
    _njit = None

if _HAS_NUMBA:
    import numpy as _np

    @_njit(cache=True, nogil=True)
    def _nb_iccdf(q):
        C_0, C_1, C_2 = 2.515516, 0.802853, 0.010328
        D_1, D_2, D_3 = 1.432788, 0.189269, 0.001308
        x = q if q <= 0.5 else 1.0 - q
        T_x = math.sqrt(-2.0 * math.log(x))
        zeta_x = ((C_2 * T_x + C_1) * T_x + C_0) / (
            ((D_3 * T_x + D_2) * T_x + D_1) * T_x + 1.0
        )
        Q_q = T_x - zeta_x
        return -Q_q if q > 0.5 else Q_q

    @_njit(cache=True, nogil=True)
    def _nb_terrain_roughness(d__meter, delta_h__meter):
        return delta_h__meter * (1.0 - 0.8 * math.exp(-d__meter / 50e3))

    @_njit(cache=True, nogil=True)
    def _nb_sigma_h(delta_h__meter):
        return 0.78 * delta_h__meter * math.exp(-0.5 * delta_h__meter**0.25)

    @_njit(cache=True, nogil=True)
    def _nb_fresnel_integral(v2):
        if v2 < 5.76:
            return 6.02 + 9.11 * math.sqrt(v2) - 1.27 * v2
        else:
            return 12.953 + 10.0 * math.log10(v2)

    @_njit(cache=True, nogil=True)
    def _nb_knife_edge_diffraction(
        d__meter, f__mhz, a_e__meter, theta_los, d_hzn0, d_hzn1
    ):
        d_ML__meter = d_hzn0 + d_hzn1
        theta_nlos = d__meter / a_e__meter - theta_los
        d_nlos__meter = d__meter - d_ML__meter
        v_1 = (
            0.0795775
            * (f__mhz / 47.7)
            * theta_nlos**2
            * d_hzn0
            * d_nlos__meter
            / (d_nlos__meter + d_hzn0)
        )
        v_2 = (
            0.0795775
            * (f__mhz / 47.7)
            * theta_nlos**2
            * d_hzn1
            * d_nlos__meter
            / (d_nlos__meter + d_hzn1)
        )
        return _nb_fresnel_integral(v_1) + _nb_fresnel_integral(v_2)

    @_njit(cache=True, nogil=True)
    def _nb_height_function(x__km, K):
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

    @_njit(cache=True, nogil=True)
    def _nb_smooth_earth_diffraction(
        d__meter,
        f__mhz,
        a_e__meter,
        theta_los,
        d_hzn0,
        d_hzn1,
        h_e0,
        h_e1,
        Z_g_re,
        Z_g_im,
    ):
        theta_nlos = d__meter / a_e__meter - theta_los
        d_ML__meter = d_hzn0 + d_hzn1

        a0 = (d__meter - d_ML__meter) / (d__meter / a_e__meter - theta_los)
        a1 = 0.5 * d_hzn0**2 / h_e0
        a2 = 0.5 * d_hzn1**2 / h_e1

        d_km_v0 = a0 * theta_nlos / 1000.0
        d_km_v1 = d_hzn0 / 1000.0
        d_km_v2 = d_hzn1 / 1000.0

        third = 1.0 / 3.0
        a_0__meter = 6370e3
        C_0_0 = (4.0 / 3.0 * a_0__meter / a0) ** third
        C_0_1 = (4.0 / 3.0 * a_0__meter / a1) ** third
        C_0_2 = (4.0 / 3.0 * a_0__meter / a2) ** third

        abs_Z_g = math.sqrt(Z_g_re**2 + Z_g_im**2)
        K_0 = 0.017778 * C_0_0 * f__mhz**third / abs_Z_g
        K_1 = 0.017778 * C_0_1 * f__mhz**third / abs_Z_g
        K_2 = 0.017778 * C_0_2 * f__mhz**third / abs_Z_g
        B_0_0 = 1.607 - K_0
        B_0_1 = 1.607 - K_1
        B_0_2 = 1.607 - K_2

        x_km_1 = B_0_1 * C_0_1**2 * f__mhz**third * d_km_v1
        x_km_2 = B_0_2 * C_0_2**2 * f__mhz**third * d_km_v2
        x_km_0 = B_0_0 * C_0_0**2 * f__mhz**third * d_km_v0 + x_km_1 + x_km_2

        F_x_0 = _nb_height_function(x_km_1, K_1)
        F_x_1 = _nb_height_function(x_km_2, K_2)

        G_x__db = 0.05751 * x_km_0 - 10.0 * math.log10(x_km_0)
        return G_x__db - F_x_0 - F_x_1 - 20.0

    @_njit(cache=True, nogil=True)
    def _nb_h0_curve(j, r):
        a = _np.array([25.0, 80.0, 177.0, 395.0, 705.0])
        b = _np.array([24.0, 45.0, 68.0, 80.0, 105.0])
        return 10.0 * math.log10(1.0 + a[j] * (1.0 / r) ** 4 + b[j] * (1.0 / r) ** 2)

    @_njit(cache=True, nogil=True)
    def _nb_h0_function(r, eta_s):
        eta_s = min(max(eta_s, 1.0), 5.0)
        i = int(eta_s)
        q = eta_s - i
        result = _nb_h0_curve(i - 1, r)
        if q != 0.0:
            result = (1.0 - q) * result + q * _nb_h0_curve(i, r)
        return result

    @_njit(cache=True, nogil=True)
    def _nb_f_function(td):
        a = _np.array([133.4, 104.6, 71.8])
        b = _np.array([0.332e-3, 0.212e-3, 0.157e-3])
        c = _np.array([-10.0, -2.5, 5.0])
        if td <= 10e3:
            i = 0
        elif td <= 70e3:
            i = 1
        else:
            i = 2
        return a[i] + b[i] * td + c[i] * math.log10(td)

    @_njit(cache=True, nogil=True)
    def _nb_curve(c1, c2, x1, x2, x3, d_e__meter):
        r = d_e__meter / x1
        return (
            (c1 + c2 / (1.0 + ((d_e__meter - x2) / x3) ** 2)) * (r * r) / (1.0 + r * r)
        )

    @_njit(cache=True, nogil=True)
    def _nb_troposcatter_loss(
        d__meter,
        theta_hzn0,
        theta_hzn1,
        d_hzn0,
        d_hzn1,
        h_e0,
        h_e1,
        a_e__meter,
        N_s,
        f__mhz,
        theta_los,
        h0,
    ):
        WN_DENOM = 47.7
        Z_0__meter = 1.7556e3
        Z_1__meter = 8.0e3
        D_0__meter = 40e3
        SQRT2 = math.sqrt(2.0)
        TROPO_H__meter = 47.7
        wn = f__mhz / WN_DENOM

        if h0 > 15.0:
            H_0 = h0
        else:
            ad = d_hzn0 - d_hzn1
            rr = h_e1 / h_e0

            if ad < 0.0:
                ad = -ad
                rr = 1.0 / rr

            theta = theta_hzn0 + theta_hzn1 + d__meter / a_e__meter

            r_1 = 2.0 * wn * theta * h_e0
            r_2 = 2.0 * wn * theta * h_e1

            if r_1 < 0.2 and r_2 < 0.2:
                return 1001.0, h0

            s = (d__meter - ad) / (d__meter + ad)
            q = min(max(0.1, rr / s), 10.0)
            s = max(0.1, s)

            h_0__meter = (d__meter - ad) * (d__meter + ad) * theta * 0.25 / d__meter

            eta_s = (h_0__meter / Z_0__meter) * (
                1.0
                + (0.031 - N_s * 2.32e-3 + N_s**2 * 5.67e-6)
                * math.exp(-(min(1.7, h_0__meter / Z_1__meter) ** 6))
            )

            H_00 = (_nb_h0_function(r_1, eta_s) + _nb_h0_function(r_2, eta_s)) / 2.0
            Delta_H_0 = min(
                H_00,
                6.0
                * (0.6 - math.log10(max(eta_s, 1.0)))
                * math.log10(s)
                * math.log10(q),
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
            _nb_f_function(th * d__meter)
            + 10.0 * math.log10(wn * TROPO_H__meter * th**4)
            - 0.1 * (N_s - 301.0) * math.exp(-th * d__meter / D_0__meter)
            + H_0
        )
        return result, h0_updated

    @_njit(cache=True, nogil=True)
    def _nb_line_of_sight_loss(
        d__meter,
        h_e0,
        h_e1,
        Z_g_re,
        Z_g_im,
        delta_h__meter,
        M_d,
        A_d0,
        d_sML__meter,
        f__mhz,
    ):
        WN_DENOM = 47.7
        PI = 3.1415926535897932384
        delta_h_d__meter = _nb_terrain_roughness(d__meter, delta_h__meter)
        sigma_h_d__meter = _nb_sigma_h(delta_h_d__meter)
        wn = f__mhz / WN_DENOM
        sin_psi = (h_e0 + h_e1) / math.sqrt(d__meter**2 + (h_e0 + h_e1) ** 2)
        Z_g = complex(Z_g_re, Z_g_im)
        R_e = (
            (sin_psi - Z_g)
            / (sin_psi + Z_g)
            * math.exp(-min(10.0, wn * sigma_h_d__meter * sin_psi))
        )
        q = R_e.real**2 + R_e.imag**2
        if q < 0.25 or q < sin_psi:
            R_e = R_e * math.sqrt(sin_psi / q)
        delta_phi = wn * 2.0 * h_e0 * h_e1 / d__meter
        if delta_phi > PI / 2.0:
            delta_phi = PI - (PI / 2.0) ** 2 / delta_phi
        rr = complex(math.cos(delta_phi), -math.sin(delta_phi)) + R_e
        A_t__db = -10.0 * math.log10(rr.real**2 + rr.imag**2)
        A_d__db = M_d * d__meter + A_d0
        w = 1.0 / (1.0 + f__mhz * delta_h__meter / max(10e3, d_sML__meter))
        return w * A_t__db + (1.0 - w) * A_d__db

    @_njit(cache=True, nogil=True)
    def _nb_diffraction_loss(
        d__meter,
        d_hzn0,
        d_hzn1,
        h_e0,
        h_e1,
        Z_g_re,
        Z_g_im,
        a_e__meter,
        delta_h__meter,
        h_tx,
        h_rx,
        mode,
        theta_los,
        d_sML__meter,
        f__mhz,
    ):
        PI = 3.1415926535897932384
        WN_DENOM = 47.7
        A_k__db = _nb_knife_edge_diffraction(
            d__meter, f__mhz, a_e__meter, theta_los, d_hzn0, d_hzn1
        )
        A_se__db = _nb_smooth_earth_diffraction(
            d__meter,
            f__mhz,
            a_e__meter,
            theta_los,
            d_hzn0,
            d_hzn1,
            h_e0,
            h_e1,
            Z_g_re,
            Z_g_im,
        )

        delta_h_dsML__meter = _nb_terrain_roughness(d_sML__meter, delta_h__meter)
        sigma_h_d__meter = _nb_sigma_h(delta_h_dsML__meter)

        A_fo__db = min(
            15.0,
            5.0 * math.log10(1.0 + 1e-5 * h_tx * h_rx * f__mhz * sigma_h_d__meter),
        )

        delta_h_d__meter2 = _nb_terrain_roughness(d__meter, delta_h__meter)
        q = h_tx * h_rx
        qk = h_e0 * h_e1 - q

        if mode == 0:
            q += 10.0

        term1 = math.sqrt(1.0 + qk / q)
        d_ML__meter = d_hzn0 + d_hzn1
        q = (term1 + (-theta_los * a_e__meter + d_ML__meter) / d__meter) * min(
            delta_h_d__meter2 * f__mhz / WN_DENOM, 6283.2
        )
        w = 25.1 / (25.1 + math.sqrt(q))
        return w * A_se__db + (1.0 - w) * A_k__db + A_fo__db

    @_njit(cache=True, nogil=True)
    def _nb_find_horizons(elevations, resolution, h_tx, h_rx, a_e__meter):
        np_ = len(elevations) - 1
        d__meter = np_ * resolution
        z_tx = elevations[0] + h_tx
        z_rx = elevations[np_] + h_rx
        theta_hzn0 = (z_rx - z_tx) / d__meter - d__meter / (2.0 * a_e__meter)
        theta_hzn1 = -(z_rx - z_tx) / d__meter - d__meter / (2.0 * a_e__meter)
        d_hzn0 = d__meter
        d_hzn1 = d__meter

        best_tx = theta_hzn0
        best_rx = theta_hzn1
        best_d_tx = d_hzn0
        best_d_rx = d_hzn1

        for idx in range(1, np_):
            d_tx = idx * resolution
            d_rx = (np_ - idx) * resolution
            t_tx = (elevations[idx] - z_tx) / d_tx - d_tx / (2.0 * a_e__meter)
            t_rx = -(z_rx - elevations[idx]) / d_rx - d_rx / (2.0 * a_e__meter)
            if t_tx > best_tx:
                best_tx = t_tx
                best_d_tx = d_tx
            if t_rx > best_rx:
                best_rx = t_rx
                best_d_rx = d_rx

        return best_tx, best_rx, best_d_tx, best_d_rx

    @_njit(cache=True, nogil=True)
    def _nb_linear_least_squares(elevations, resolution, d_start, d_end):
        np_ = len(elevations) - 1
        i_start = int(max(d_start / resolution - 0.0, 0.0))
        i_end = np_ - int(max(np_ - d_end / resolution, 0.0))

        if i_end <= i_start:
            i_start = int(max(i_start - 1.0, 0.0))
            i_end = np_ - int(max(np_ - (i_end + 1.0), 0.0))

        x_length = float(i_end - i_start)
        mid_shift = -0.5 * x_length
        mid_shift_end = i_end + mid_shift

        sum_y = 0.5 * (elevations[i_start] + elevations[i_end])
        scaled_sum_y = 0.5 * (elevations[i_start] - elevations[i_end]) * mid_shift

        n_inner = int(x_length) - 1
        for k in range(n_inner):
            idx = i_start + 1 + k
            offset = mid_shift + 1.0 + k
            sum_y += elevations[idx]
            scaled_sum_y += elevations[idx] * offset

        sum_y /= x_length
        scaled_sum_y = scaled_sum_y * 12.0 / ((x_length * x_length + 2.0) * x_length)

        fit_y1 = sum_y - scaled_sum_y * mid_shift_end
        fit_y2 = sum_y + scaled_sum_y * (np_ - mid_shift_end)
        return fit_y1, fit_y2

    @_njit(cache=True, nogil=True)
    def _nb_compute_delta_h(elevations, resolution, d_start__meter, d_end__meter):
        np_ = len(elevations) - 1
        x_start_idx = d_start__meter / resolution
        x_end_idx = d_end__meter / resolution

        if x_end_idx - x_start_idx < 2.0:
            return 0.0

        p10 = int(0.1 * (x_end_idx - x_start_idx + 8.0))
        p10 = min(max(4, p10), 25)

        n = 10 * p10 - 5
        p90 = n - p10

        np_s = float(n - 1)
        x_step = (x_end_idx - x_start_idx) / np_s

        i = int(x_start_idx)
        x_pos = x_start_idx - float(i + 1)

        s_arr = _np.empty(n, dtype=_np.float64)
        for k in range(n):
            while x_pos > 0.0 and (i + 1) < np_:
                x_pos -= 1.0
                i += 1
            s_arr[k] = elevations[i + 1] + (elevations[i + 1] - elevations[i]) * x_pos
            x_pos += x_step

        fit_y1, fit_y2 = _nb_linear_least_squares(
            elevations, resolution, d_start__meter, d_end__meter
        )
        fit_slope = (fit_y2 - fit_y1) / np_s

        diffs = _np.empty(n, dtype=_np.float64)
        for k in range(n):
            diffs[k] = s_arr[k] - (fit_y1 + fit_slope * k)

        diffs_neg = _np.empty(n, dtype=_np.float64)
        for k in range(n):
            diffs_neg[k] = -diffs[k]

        partial = _np.empty(n, dtype=_np.float64)
        for k in range(n):
            partial[k] = -diffs[k]

        diffs_neg.sort()
        q10 = diffs_neg[min(p10 - 1, n - 1)]
        partial.sort()
        q90 = partial[min(p90, n - 1)]

        delta_h_rough = q10 - q90

        return delta_h_rough / (
            1.0 - 0.8 * math.exp(-(d_end__meter - d_start__meter) / 50e3)
        )

    @_njit(cache=True, nogil=True)
    def _nb_variability(
        time_pct,
        location_pct,
        situation_pct,
        h_e0,
        h_e1,
        delta_h__meter,
        f__mhz,
        d__meter,
        A_ref__db,
        climate_idx,
    ):
        third = 1.0 / 3.0
        WN_DENOM = 47.7
        D_SCALE__meter = 100e3
        a_9000__meter = 9000e3

        z_T = _nb_iccdf(time_pct / 100.0)
        z_L = _nb_iccdf(location_pct / 100.0)
        z_S = _nb_iccdf(situation_pct / 100.0)
        ci = climate_idx

        _ALL_YEAR_0 = _np.array([-9.67, -0.62, 1.26, -9.21, -0.62, -0.39, 3.15])
        _ALL_YEAR_1 = _np.array([12.7, 9.19, 15.5, 9.05, 9.19, 2.86, 857.9])
        _ALL_YEAR_2 = _np.array(
            [144.9e3, 228.9e3, 262.6e3, 84.1e3, 228.9e3, 141.7e3, 2222.0e3]
        )
        _ALL_YEAR_3 = _np.array(
            [190.3e3, 205.2e3, 185.2e3, 101.1e3, 205.2e3, 315.9e3, 164.8e3]
        )
        _ALL_YEAR_4 = _np.array(
            [133.8e3, 143.6e3, 99.8e3, 98.6e3, 143.6e3, 167.4e3, 116.3e3]
        )
        _BSM1 = _np.array([2.13, 2.66, 6.11, 1.98, 2.68, 6.86, 8.51])
        _BSM2 = _np.array([159.5, 7.67, 6.65, 13.11, 7.16, 10.38, 169.8])
        _XSM1 = _np.array(
            [762.2e3, 100.4e3, 138.2e3, 139.1e3, 93.7e3, 187.8e3, 609.3e3]
        )
        _XSM2 = _np.array(
            [123.6e3, 172.5e3, 242.2e3, 132.7e3, 186.8e3, 169.6e3, 119.9e3]
        )
        _XSM3 = _np.array(
            [94.5e3, 136.4e3, 178.6e3, 193.5e3, 133.5e3, 108.9e3, 106.6e3]
        )
        _BSP1 = _np.array([2.11, 6.87, 10.08, 3.68, 4.75, 8.58, 8.43])
        _BSP2 = _np.array([102.3, 15.53, 9.60, 159.3, 8.12, 13.97, 8.19])
        _XSP1 = _np.array(
            [636.9e3, 138.7e3, 165.3e3, 464.0e3, 93.2e3, 216.0e3, 136.2e3]
        )
        _XSP2 = _np.array(
            [134.8e3, 143.7e3, 225.3e3, 93.1e3, 135.9e3, 152.7e3, 188.3e3]
        )
        _XSP3 = _np.array([95.6e3, 98.6e3, 129.7e3, 94.2e3, 113.4e3, 122.7e3, 122.9e3])
        _C_D = _np.array([1.224, 0.801, 1.380, 1.000, 1.224, 1.518, 1.518])
        _Z_D = _np.array([1.282, 2.161, 1.282, 20.0, 1.282, 1.282, 1.282])
        _BFM1 = _np.array([1.0, 1.0, 1.0, 1.0, 0.92, 1.0, 1.0])
        _BFM2 = _np.array([0.0, 0.0, 0.0, 0.0, 0.25, 0.0, 0.0])
        _BFM3 = _np.array([0.0, 0.0, 0.0, 0.0, 1.77, 0.0, 0.0])
        _BFP1 = _np.array([1.0, 0.93, 1.0, 0.93, 0.93, 1.0, 1.0])
        _BFP2 = _np.array([0.0, 0.31, 0.0, 0.19, 0.31, 0.0, 0.0])
        _BFP3 = _np.array([0.0, 2.00, 0.0, 1.79, 2.00, 0.0, 0.0])

        wn = f__mhz / WN_DENOM

        d_ex__meter = (
            math.sqrt(2 * a_9000__meter * h_e0)
            + math.sqrt(2 * a_9000__meter * h_e1)
            + (575.7e12 / wn) ** third
        )
        if d__meter < d_ex__meter:
            d_e__meter = 130e3 * d__meter / d_ex__meter
        else:
            d_e__meter = 130e3 + d__meter - d_ex__meter

        sigma_S = 5.0 + 3.0 * math.exp(-d_e__meter / D_SCALE__meter)

        V_med__db = _nb_curve(
            _ALL_YEAR_0[ci],
            _ALL_YEAR_1[ci],
            _ALL_YEAR_2[ci],
            _ALL_YEAR_3[ci],
            _ALL_YEAR_4[ci],
            d_e__meter,
        )

        q_log = math.log(max(0.133 * wn, 1e-30))
        g_minus = _BFM1[ci] + _BFM2[ci] / (pow(_BFM3[ci] * q_log, 2) + 1.0)
        g_plus = _BFP1[ci] + _BFP2[ci] / (pow(_BFP3[ci] * q_log, 2) + 1.0)

        sigma_T_minus = (
            _nb_curve(_BSM1[ci], _BSM2[ci], _XSM1[ci], _XSM2[ci], _XSM3[ci], d_e__meter)
            * g_minus
        )
        sigma_T_plus = (
            _nb_curve(_BSP1[ci], _BSP2[ci], _XSP1[ci], _XSP2[ci], _XSP3[ci], d_e__meter)
            * g_plus
        )

        sigma_TD = _C_D[ci] * sigma_T_plus
        tgtd = (sigma_T_plus - sigma_TD) * _Z_D[ci]

        if z_T < 0.0:
            sigma_T = sigma_T_minus
        elif z_T <= _Z_D[ci]:
            sigma_T = sigma_T_plus
        else:
            sigma_T = sigma_TD + tgtd / z_T

        Y_T = sigma_T * z_T

        delta_h_d__meter = _nb_terrain_roughness(d__meter, delta_h__meter)
        sigma_L = 10.0 * wn * delta_h_d__meter / (wn * delta_h_d__meter + 13.0)
        Y_L = sigma_L * z_L

        Y_S_temp = sigma_S**2 + Y_T**2 / (7.8 + z_S**2) + Y_L**2 / (24.0 + z_S**2)

        Y_S = math.sqrt(Y_S_temp) * z_S
        Y_R = Y_T + Y_L

        result = A_ref__db - V_med__db - Y_R - Y_S

        if result < 0.0:
            result = result * (29.0 - result) / (29.0 - 10.0 * result)

        return result

    @_njit(cache=True, nogil=True)
    def nb_itm_p2p_loss(
        h_tx__meter,
        h_rx__meter,
        elevations,
        resolution,
        climate_idx,
        N_0,
        f__mhz,
        polarization,
        epsilon,
        sigma,
        time_pct,
        location_pct,
        situation_pct,
    ):
        GAMMA_A = 157e-9
        PI = 3.1415926535897932384
        SQRT2 = math.sqrt(2.0)
        third = 1.0 / 3.0

        np_ = len(elevations) - 1
        p10 = int(0.1 * np_)
        h_sys__meter = 0.0
        count = 0
        for i in range(p10, np_ - p10 + 1):
            h_sys__meter += elevations[i]
            count += 1
        if count > 0:
            h_sys__meter /= count

        if h_sys__meter == 0.0:
            N_s = N_0
        else:
            N_s = N_0 * math.exp(-h_sys__meter / 9460.0)

        gamma_e = GAMMA_A * (1.0 - 0.04665 * math.exp(N_s / 179.3))
        a_e__meter = 1.0 / gamma_e

        ep_r_re = epsilon
        ep_r_im = 18000.0 * sigma / f__mhz
        Z_g_re_sq = ep_r_re - 1.0
        Z_g_im_sq = ep_r_im
        Z_g_re = math.sqrt(math.sqrt(Z_g_re_sq**2 + Z_g_im_sq**2))
        Z_g_im_signed = 0.0

        re_sq = Z_g_re_sq
        im_sq = Z_g_im_sq
        mag_sq = re_sq + im_sq
        Z_g_re = math.sqrt((math.sqrt(mag_sq) + re_sq) / 2.0)
        Z_g_im_signed = math.sqrt(max(0.0, (math.sqrt(mag_sq) - re_sq) / 2.0))
        if im_sq < 0:
            Z_g_im_signed = -Z_g_im_signed

        if polarization == 1:
            ep_r_mag_sq = ep_r_re**2 + ep_r_im**2
            Z_g_re_over = (Z_g_re * ep_r_re + Z_g_im_signed * ep_r_im) / ep_r_mag_sq
            Z_g_im_over = (Z_g_im_signed * ep_r_re - Z_g_re * ep_r_im) / ep_r_mag_sq
            Z_g_re = Z_g_re_over
            Z_g_im_signed = Z_g_im_over

        theta_hzn0, theta_hzn1, d_hzn0, d_hzn1 = _nb_find_horizons(
            elevations, resolution, h_tx__meter, h_rx__meter, a_e__meter
        )

        d__meter = np_ * resolution

        d_start__meter = min(15.0 * h_tx__meter, 0.1 * d_hzn0)
        d_end__meter = d__meter - min(15.0 * h_rx__meter, 0.1 * d_hzn1)

        delta_h__meter = _nb_compute_delta_h(
            elevations, resolution, d_start__meter, d_end__meter
        )

        h_e0 = 0.0
        h_e1 = 0.0

        if d_hzn0 + d_hzn1 > 1.5 * d__meter:
            fit_tx, fit_rx = _nb_linear_least_squares(
                elevations, resolution, d_start__meter, d_end__meter
            )
            h_e0 = h_tx__meter + max(elevations[0] - fit_tx, 0.0)
            h_e1 = h_rx__meter + max(elevations[np_] - fit_rx, 0.0)

            d_hzn0_new = math.sqrt(2.0 * h_e0 * a_e__meter) * math.exp(
                -0.07 * math.sqrt(delta_h__meter / max(h_e0, 5.0))
            )
            d_hzn1_new = math.sqrt(2.0 * h_e1 * a_e__meter) * math.exp(
                -0.07 * math.sqrt(delta_h__meter / max(h_e1, 5.0))
            )

            if d_hzn0_new + d_hzn1_new <= d__meter:
                q = (d__meter / (d_hzn0_new + d_hzn1_new)) ** 2
                h_e0 *= q
                h_e1 *= q
                d_hzn0 = math.sqrt(2.0 * h_e0 * a_e__meter) * math.exp(
                    -0.07 * math.sqrt(delta_h__meter / max(h_e0, 5.0))
                )
                d_hzn1 = math.sqrt(2.0 * h_e1 * a_e__meter) * math.exp(
                    -0.07 * math.sqrt(delta_h__meter / max(h_e1, 5.0))
                )

            for i in range(2):
                q_hor = math.sqrt(2.0 * (h_e0 if i == 0 else h_e1) * a_e__meter)
                if i == 0:
                    theta_hzn0 = (
                        0.65 * delta_h__meter * (q_hor / d_hzn0 - 1.0) - 2.0 * h_e0
                    ) / q_hor
                else:
                    theta_hzn1 = (
                        0.65 * delta_h__meter * (q_hor / d_hzn1 - 1.0) - 2.0 * h_e1
                    ) / q_hor
        else:
            fit_tx, _ = _nb_linear_least_squares(
                elevations, resolution, d_start__meter, 0.9 * d_hzn0
            )
            h_e0 = h_tx__meter + max(elevations[0] - fit_tx, 0.0)
            _, fit_rx = _nb_linear_least_squares(
                elevations, resolution, d__meter - 0.9 * d_hzn1, d_end__meter
            )
            h_e1 = h_rx__meter + max(elevations[np_] - fit_rx, 0.0)

        theta_los = -max(theta_hzn0 + theta_hzn1, -d__meter / a_e__meter)

        d_hzn_s0 = math.sqrt(2.0 * h_e0 * a_e__meter)
        d_hzn_s1 = math.sqrt(2.0 * h_e1 * a_e__meter)
        d_sML__meter = d_hzn_s0 + d_hzn_s1
        d_ML__meter = d_hzn0 + d_hzn1

        d_diff_step = 10.0 * (a_e__meter**2 / f__mhz) ** third
        d_3__meter = max(d_sML__meter, d_ML__meter + 0.5 * d_diff_step)
        d_4__meter = d_3__meter + d_diff_step

        A_3__db = _nb_diffraction_loss(
            d_3__meter,
            d_hzn0,
            d_hzn1,
            h_e0,
            h_e1,
            Z_g_re,
            Z_g_im_signed,
            a_e__meter,
            delta_h__meter,
            h_tx__meter,
            h_rx__meter,
            0,
            theta_los,
            d_sML__meter,
            f__mhz,
        )
        A_4__db = _nb_diffraction_loss(
            d_4__meter,
            d_hzn0,
            d_hzn1,
            h_e0,
            h_e1,
            Z_g_re,
            Z_g_im_signed,
            a_e__meter,
            delta_h__meter,
            h_tx__meter,
            h_rx__meter,
            0,
            theta_los,
            d_sML__meter,
            f__mhz,
        )

        M_d = (A_4__db - A_3__db) / (d_4__meter - d_3__meter)
        A_d0__db = A_3__db - M_d * d_3__meter

        A_ref__db = 0.0
        prop_mode = 1

        if d__meter < d_sML__meter:
            A_sML__db = d_sML__meter * M_d + A_d0__db
            d_0__meter = 0.04 * f__mhz * h_e0 * h_e1

            if A_d0__db >= 0.0:
                d_0__meter = min(d_0__meter, 0.5 * d_ML__meter)
                d_1__meter = d_0__meter + 0.25 * (d_ML__meter - d_0__meter)
            else:
                d_1__meter = max(-A_d0__db / M_d, 0.25 * d_ML__meter)

            A_1__db = _nb_line_of_sight_loss(
                d_1__meter,
                h_e0,
                h_e1,
                Z_g_re,
                Z_g_im_signed,
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
                A_0__db = _nb_line_of_sight_loss(
                    d_0__meter,
                    h_e0,
                    h_e1,
                    Z_g_re,
                    Z_g_im_signed,
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

            A_o__db = (
                A_sML__db - kHat_1 * d_sML__meter - kHat_2 * math.log(d_sML__meter)
            )
            A_ref__db = A_o__db + kHat_1 * d__meter + kHat_2 * math.log(d__meter)
            prop_mode = 1
        else:
            d_5__meter = d_ML__meter + 200e3
            d_6__meter = d_ML__meter + 400e3

            h0 = -1.0
            A_6__db, h0 = _nb_troposcatter_loss(
                d_6__meter,
                theta_hzn0,
                theta_hzn1,
                d_hzn0,
                d_hzn1,
                h_e0,
                h_e1,
                a_e__meter,
                N_s,
                f__mhz,
                theta_los,
                h0,
            )
            A_5__db, h0 = _nb_troposcatter_loss(
                d_5__meter,
                theta_hzn0,
                theta_hzn1,
                d_hzn0,
                d_hzn1,
                h_e0,
                h_e1,
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
                        + 1.088 * (a_e__meter**2 / f__mhz) ** third * math.log(f__mhz),
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
                prop_mode = 3
            else:
                A_ref__db = M_d * d__meter + A_d0__db
                prop_mode = 2

        A_ref__db = max(A_ref__db, 0.0)

        result_db = _nb_variability(
            time_pct,
            location_pct,
            situation_pct,
            h_e0,
            h_e1,
            delta_h__meter,
            f__mhz,
            d__meter,
            A_ref__db,
            climate_idx,
        )

        A_fs__db = (
            32.45 + 20.0 * math.log10(f__mhz) + 20.0 * math.log10(d__meter / 1000.0)
        )
        return result_db + A_fs__db


def nb_itm_p2p_loss_pure(
    h_tx__meter,
    h_rx__meter,
    pfl_elevations,
    pfl_resolution,
    climate_idx,
    N_0,
    f__mhz,
    polarization,
    epsilon,
    sigma,
    time_pct,
    location_pct,
    situation_pct,
):
    """Pure-Python fallback: call the original itm modules."""
    from .radio import itm_p2p_loss, build_pfl

    pfl = build_pfl(pfl_elevations, pfl_resolution)
    result = itm_p2p_loss(
        h_tx__meter=h_tx__meter,
        h_rx__meter=h_rx__meter,
        profile=pfl,
        climate=climate_idx,
        N0=N_0,
        f__mhz=f__mhz,
        polarization=polarization,
        epsilon=epsilon,
        sigma=sigma,
        time_pct=time_pct,
        location_pct=location_pct,
        situation_pct=situation_pct,
    )
    if not math.isfinite(result.loss_db) or result.loss_db > 400.0:
        return None
    prx = (h_tx__meter + 8.0 - 2.0) + 2.0 - result.loss_db
    return (result.loss_db, prx, result.mode if hasattr(result, "mode") else 0)


def compute_itm_p2p(
    h_tx__meter,
    h_rx__meter,
    elevations,
    resolution,
    climate_idx,
    N_0,
    f__mhz,
    polarization,
    epsilon,
    sigma,
    time_pct,
    location_pct,
    situation_pct,
    eirp_dbm,
    ant_gain_adj,
    rx_gain_dbi,
):
    """Compute ITM p2p loss, using numba if available, else pure-Python fallback."""
    if _HAS_NUMBA:
        try:
            loss_db = nb_itm_p2p_loss(
                h_tx__meter,
                h_rx__meter,
                elevations,
                resolution,
                climate_idx,
                N_0,
                f__mhz,
                polarization,
                epsilon,
                sigma,
                time_pct,
                location_pct,
                situation_pct,
            )
            if not math.isfinite(loss_db) or loss_db > 400.0:
                return None
            prx = eirp_dbm + ant_gain_adj + rx_gain_dbi - loss_db
            return (loss_db, prx)
        except Exception:
            pass

    from .radio import itm_p2p_loss, build_pfl

    elev_list = (
        elevations.tolist() if hasattr(elevations, "tolist") else list(elevations)
    )
    pfl = build_pfl(elev_list, resolution)
    result = itm_p2p_loss(
        h_tx__meter=h_tx__meter,
        h_rx__meter=h_rx__meter,
        profile=pfl,
        climate=climate_idx,
        N0=N_0,
        f__mhz=f__mhz,
        polarization=polarization,
        epsilon=epsilon,
        sigma=sigma,
        time_pct=time_pct,
        location_pct=location_pct,
        situation_pct=situation_pct,
    )
    if not math.isfinite(result.loss_db) or result.loss_db > 400.0:
        return None
    prx = eirp_dbm + ant_gain_adj + rx_gain_dbi - result.loss_db
    return (result.loss_db, prx)
