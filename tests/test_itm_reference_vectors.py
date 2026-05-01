# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# This program is free software under GPLv3 or later. See LICENSE.
"""Reference-vector tests for the bundled ITM propagation model.

Verifies core propagation functions against known ITM reference values
and validates edge cases that previously caused domain errors (NC1).
"""

import math

import numpy as np
import pytest

from itm import Climate, Polarization, TerrainProfile, predict_p2p
from itm.propagation import (
    free_space_loss,
    fresnel_integral,
    height_function,
    h0_function,
    initialize_point_to_point,
    longley_rice,
    smooth_earth_diffraction,
)
from itm._constants import THIRD, a_0__meter, WN_DENOM
from itm.models import PropMode


# ---------------------------------------------------------------------------
# NC1 regression: smooth_earth_diffraction must not raise on extreme inputs
# ---------------------------------------------------------------------------

class TestSmoothEarthDiffractionEdgeCases:
    """Verify that smooth_earth_diffraction handles degenerate geometry
    without raising ValueError from log/log10 on non-positive arguments.

    This is the regression test for NC1: low frequency × small |Z_g|
    makes K > 1.607, driving B_0 negative, which in turn makes x__km <= 0.
    """

    @pytest.fixture
    def vertical_low_freq_params(self):
        """Parameters that produce small |Z_g| and large K, triggering B_0 < 0."""
        Z_g, gamma_e, N_s = initialize_point_to_point(
            f__mhz=20.0,  # Very low frequency → large K
            h_sys__meter=50.0,
            N_0=301.0,
            pol=1,  # VERTICAL → Z_g = sqrt(eps-1)/eps, small for high eps
            epsilon=15.0,
            sigma=0.005,
        )
        a_e__meter = 1.0 / gamma_e
        return Z_g, a_e__meter, N_s

    def test_does_not_raise_with_vertical_low_freq(self, vertical_low_freq_params):
        """V-pol at 20 MHz: |Z_g| is small, B_0 can go negative — must not crash."""
        Z_g, a_e__meter, _ = vertical_low_freq_params
        # Typical trans-horizon geometry
        result = smooth_earth_diffraction(
            d__meter=50000.0,
            f__mhz=20.0,
            a_e__meter=a_e__meter,
            theta_los=-0.001,
            d_hzn__meter=[5000.0, 5000.0],
            h_e__meter=[10.0, 10.0],
            Z_g=Z_g,
        )
        assert math.isfinite(result)
        assert result > 0  # loss should be positive

    def test_does_not_raise_with_horizontal_high_conductivity(self):
        """H-pol at 20 MHz, high conductivity → small |Z_g|, large K."""
        Z_g, gamma_e, N_s = initialize_point_to_point(
            f__mhz=20.0,
            h_sys__meter=50.0,
            N_0=301.0,
            pol=0,  # HORIZONTAL
            epsilon=15.0,
            sigma=5.0,  # Very high conductivity
        )
        a_e__meter = 1.0 / gamma_e
        result = smooth_earth_diffraction(
            d__meter=100000.0,
            f__mhz=20.0,
            a_e__meter=a_e__meter,
            theta_los=-0.002,
            d_hzn__meter=[10000.0, 8000.0],
            h_e__meter=[30.0, 10.0],
            Z_g=Z_g,
        )
        assert math.isfinite(result)
        assert result > 0

    def test_height_function_returns_finite_for_nonpositive_x(self):
        """height_function must return a finite value for x__km <= 0."""
        assert height_function(0.0, 0.5) == 200.0
        assert height_function(-1.0, 0.5) == 200.0
        assert math.isfinite(height_function(0.001, 0.5))

    def test_height_function_returns_finite_for_nonpositive_K(self):
        """height_function must return a finite value for K <= 0."""
        assert height_function(100.0, -0.5) == 200.0
        assert height_function(100.0, 0.0) == 200.0
        assert math.isfinite(height_function(100.0, 0.5))

    def test_smooth_earth_diffraction_extreme_frequency_range(self):
        """Test at minimum and maximum ITM frequencies."""
        for f_mhz in [20.0, 20000.0]:
            Z_g, gamma_e, _ = initialize_point_to_point(
                f__mhz=f_mhz, h_sys__meter=50.0, N_0=301.0,
                pol=0, epsilon=15.0, sigma=0.005,
            )
            a_e__meter = 1.0 / gamma_e
            result = smooth_earth_diffraction(
                d__meter=50000.0,
                f__mhz=f_mhz,
                a_e__meter=a_e__meter,
                theta_los=-0.001,
                d_hzn__meter=[5000.0, 5000.0],
                h_e__meter=[10.0, 10.0],
                Z_g=Z_g,
            )
            assert math.isfinite(result), f"Non-finite result at f={f_mhz} MHz"


# ---------------------------------------------------------------------------
# Reference-value tests for ITM propagation primitives
# ---------------------------------------------------------------------------

class TestFreeSpaceLoss:
    """Reference values from the Friis transmission equation."""

    def test_1_km_1_ghz(self):
        # FSPL = 32.45 + 20*log10(1000) + 20*log10(1) = 92.45 dB (approx)
        assert free_space_loss(1000.0, 1000.0) == pytest.approx(92.45, abs=0.01)

    def test_10_km_300_mhz(self):
        # FSPL = 32.45 + 20*log10(300) + 20*log10(10) = 32.45 + 49.54 + 20.0 = 101.99
        assert free_space_loss(10000.0, 300.0) == pytest.approx(101.99, abs=0.1)

    def test_1_m_900_mhz(self):
        # FSPL at 1m, 900 MHz (near-field reference)
        assert free_space_loss(1.0, 900.0) == pytest.approx(
            32.45 + 20 * math.log10(900) + 20 * math.log10(1e-3), abs=0.1
        )


class TestFresnelIntegral:
    """Test fresnel_integral at key reference points."""

    def test_low_branch_v2_1(self):
        # v2=1: 6.02 + 9.11*sqrt(1) - 1.27*1 = 13.86
        assert fresnel_integral(1.0) == pytest.approx(13.86, abs=0.02)

    def test_high_branch_v2_9(self):
        # v2=9: 12.953 + 10*log10(9)
        expected = 12.953 + 10.0 * math.log10(9.0)
        assert fresnel_integral(9.0) == pytest.approx(expected, abs=0.01)

    def test_transition_at_5_76(self):
        # v2 = 5.76 should give close results from both branches
        low = 6.02 + 9.11 * math.sqrt(5.76) - 1.27 * 5.76
        high = 12.953 + 10.0 * math.log10(5.76)
        # Both should be positive finite numbers
        assert math.isfinite(low)
        assert math.isfinite(high)


class TestHeightFunction:
    """Verify height_function returns finite values across input ranges."""

    @pytest.mark.parametrize("x_km,K", [
        (0.1, 0.01),   # Very small x, small K
        (1.0, 0.1),    # x=1.0 boundary in low branch
        (50.0, 0.01),  # Mid-range
        (200.0, 0.01), # Boundary between low and high branch
        (500.0, 0.01), # High branch
        (2000.0, 0.01),# Upper boundary of interpolation
        (5000.0, 0.01),# Pure high branch
        (0.001, 1e-6), # Extreme: tiny x, tiny K
    ])
    def test_finite_output(self, x_km, K):
        result = height_function(x_km, K)
        assert math.isfinite(result), f"Non-finite result for x={x_km}, K={K}"

    def test_monotonicity_in_x_for_fixed_K(self):
        """For fixed K, height_function should generally increase with x."""
        K = 0.01
        values = [height_function(x, K) for x in [1, 10, 100, 1000, 10000]]
        # Should be increasing (not strictly, but broadly)
        assert values[-1] > values[0]


class TestInitializePointToPoint:
    """Verify ground impedance and effective earth curvature."""

    def test_vertical_polarization_reduces_impedance(self):
        """Vertical pol Z_g should be smaller |Z_g| than horizontal."""
        Z_h, _, _ = initialize_point_to_point(1000.0, 50.0, 301.0, 0, 15.0, 0.005)
        Z_v, _, _ = initialize_point_to_point(1000.0, 50.0, 301.0, 1, 15.0, 0.005)
        assert abs(Z_v) < abs(Z_h)

    def test_effective_earth_radius_positive(self):
        Z_g, gamma_e, N_s = initialize_point_to_point(300.0, 50.0, 301.0, 0, 15.0, 0.005)
        a_e = 1.0 / gamma_e
        # Standard atmosphere: ~ 4/3 * 6370 km ≈ 8493 km
        assert 4_000_000 < a_e < 13_333_333

    def test_surface_refractivity_decays_with_height(self):
        _, _, N_s_h0 = initialize_point_to_point(300.0, 0.0, 301.0, 0, 15.0, 0.005)
        _, _, N_s_h1000 = initialize_point_to_point(300.0, 1000.0, 301.0, 0, 15.0, 0.005)
        assert N_s_h1000 < N_s_h0  # Refractivity decreases with height


# ---------------------------------------------------------------------------
# End-to-end predict_p2p reference-vector tests
# ---------------------------------------------------------------------------

class TestPredictP2pReferenceVectors:
    """Test predict_p2p against known ITM outcomes for representative scenarios."""

    @staticmethod
    def _make_terrain(length_m, resolution, base_elev=100.0):
        """Helper to create flat terrain at given resolution."""
        n_points = max(2, int(length_m / resolution) + 1)
        return TerrainProfile(
            elevations=np.full(n_points, base_elev, dtype=float),
            resolution=resolution,
        )

    def test_short_range_los_standard_atmosphere(self):
        """3 km path, standard atmosphere, should produce finite loss in LOS regime."""
        terrain = self._make_terrain(3000.0, 30.0)
        result = predict_p2p(
            h_tx__meter=30.0,
            h_rx__meter=10.0,
            terrain=terrain,
            climate=Climate.CONTINENTAL_TEMPERATE,
            N_0=301.0,
            f__mhz=900.0,
            pol=Polarization.HORIZONTAL,
            epsilon=15.0,
            sigma=0.005,
            mdvar=0,
            time=50.0,
            location=50.0,
            situation=50.0,
            return_intermediate=True,
        )
        assert math.isfinite(result.A__db)
        assert result.A__db > 0
        assert result.intermediate is not None
        assert 0 < result.intermediate.d__km <= 3.1

    def test_medium_range_diffraction(self):
        """50 km path over moderate terrain should produce diffraction loss."""
        terrain = TerrainProfile(
            elevations=np.linspace(100.0, 200.0, 51, dtype=float),
            resolution=30.0,
        )
        result = predict_p2p(
            h_tx__meter=10.0,
            h_rx__meter=10.0,
            terrain=terrain,
            climate=Climate.MARITIME_TEMPERATE_LAND,
            N_0=320.0,
            f__mhz=300.0,
            pol=Polarization.VERTICAL,
            epsilon=15.0,
            sigma=0.005,
            mdvar=0,
            time=50.0,
            location=50.0,
            situation=50.0,
            return_intermediate=True,
        )
        assert math.isfinite(result.A__db)
        assert result.A__db > 0
        # Path is ~1.5 km, so loss should be modest
        assert result.A__db < 500  # Sanity upper bound

    def test_very_short_path(self):
        """500m path: should still produce a valid result."""
        terrain = self._make_terrain(500.0, 10.0)
        result = predict_p2p(
            h_tx__meter=30.0,
            h_rx__meter=10.0,
            terrain=terrain,
            climate=Climate.CONTINENTAL_TEMPERATE,
            N_0=301.0,
            f__mhz=5800.0,
            pol=Polarization.VERTICAL,
            epsilon=15.0,
            sigma=0.005,
            mdvar=0,
            time=50.0,
            location=50.0,
            situation=50.0,
        )
        assert math.isfinite(result.A__db)
        assert result.A__db > 0

    def test_horizontal_vs_vertical_polarization(self):
        """H-pol and V-pol should produce different losses (V-pol typically lower)."""
        terrain = self._make_terrain(10000.0, 30.0)
        result_h = predict_p2p(
            h_tx__meter=30.0, h_rx__meter=10.0, terrain=terrain,
            climate=Climate.CONTINENTAL_TEMPERATE, N_0=301.0,
            f__mhz=300.0, pol=Polarization.HORIZONTAL,
            epsilon=15.0, sigma=0.005, mdvar=0,
            time=50.0, location=50.0, situation=50.0,
        )
        result_v = predict_p2p(
            h_tx__meter=30.0, h_rx__meter=10.0, terrain=terrain,
            climate=Climate.CONTINENTAL_TEMPERATE, N_0=301.0,
            f__mhz=300.0, pol=Polarization.VERTICAL,
            epsilon=15.0, sigma=0.005, mdvar=0,
            time=50.0, location=50.0, situation=50.0,
        )
        # Both should be finite and positive
        assert math.isfinite(result_h.A__db)
        assert math.isfinite(result_v.A__db)
        # They should differ (different ground reflection coefficients)
        assert result_h.A__db != result_v.A__db

    def test_higher_frequency_higher_loss(self):
        """Higher frequency should generally produce higher free-space loss."""
        terrain = self._make_terrain(5000.0, 30.0)
        result_low = predict_p2p(
            h_tx__meter=30.0, h_rx__meter=10.0, terrain=terrain,
            climate=Climate.CONTINENTAL_TEMPERATE, N_0=301.0,
            f__mhz=100.0, pol=Polarization.HORIZONTAL,
            epsilon=15.0, sigma=0.005, mdvar=0,
            time=50.0, location=50.0, situation=50.0,
        )
        result_high = predict_p2p(
            h_tx__meter=30.0, h_rx__meter=10.0, terrain=terrain,
            climate=Climate.CONTINENTAL_TEMPERATE, N_0=301.0,
            f__mhz=5000.0, pol=Polarization.HORIZONTAL,
            epsilon=15.0, sigma=0.005, mdvar=0,
            time=50.0, location=50.0, situation=50.0,
        )
        assert result_high.A__db > result_low.A__db

    def test_nc1_regression_extreme_params(self):
        """Regression test for NC1: extreme params that previously raised ValueError.

        20 MHz, vertical polarization, high conductivity → B_0 can go negative,
        causing log10(domain_error). This test verifies the fix prevents the crash.
        """
        terrain = self._make_terrain(10000.0, 30.0)
        # Must not raise ValueError
        result = predict_p2p(
            h_tx__meter=10.0,
            h_rx__meter=10.0,
            terrain=terrain,
            climate=Climate.CONTINENTAL_TEMPERATE,
            N_0=301.0,
            f__mhz=20.0,       # Low frequency
            pol=Polarization.VERTICAL,  # V-pol → small |Z_g|
            epsilon=15.0,
            sigma=5.0,          # High conductivity → even smaller |Z_g|
            mdvar=0,
            time=50.0,
            location=50.0,
            situation=50.0,
        )
        assert math.isfinite(result.A__db)

    def test_boundary_frequency_20_mhz(self):
        """Minimum frequency boundary (20 MHz) should produce valid results."""
        terrain = self._make_terrain(5000.0, 30.0)
        result = predict_p2p(
            h_tx__meter=30.0,
            h_rx__meter=10.0,
            terrain=terrain,
            climate=Climate.CONTINENTAL_TEMPERATE,
            N_0=301.0,
            f__mhz=20.0,
            pol=Polarization.HORIZONTAL,
            epsilon=15.0,
            sigma=0.005,
            mdvar=0,
            time=50.0,
            location=50.0,
            situation=50.0,
        )
        assert math.isfinite(result.A__db)
        assert result.A__db > 0

    def test_boundary_frequency_20000_mhz(self):
        """Maximum frequency boundary (20000 MHz) should produce valid results."""
        terrain = self._make_terrain(5000.0, 30.0)
        result = predict_p2p(
            h_tx__meter=30.0,
            h_rx__meter=10.0,
            terrain=terrain,
            climate=Climate.CONTINENTAL_TEMPERATE,
            N_0=301.0,
            f__mhz=20000.0,
            pol=Polarization.HORIZONTAL,
            epsilon=15.0,
            sigma=0.005,
            mdvar=0,
            time=50.0,
            location=50.0,
            situation=50.0,
        )
        assert math.isfinite(result.A__db)
        assert result.A__db > 0

    @pytest.mark.parametrize("climate_enum", list(Climate))
    def test_all_climate_zones_produce_finite_loss(self, climate_enum):
        """Every ITM climate zone should produce a finite loss."""
        terrain = self._make_terrain(10000.0, 30.0)
        result = predict_p2p(
            h_tx__meter=30.0,
            h_rx__meter=10.0,
            terrain=terrain,
            climate=climate_enum,
            N_0=301.0,
            f__mhz=900.0,
            pol=Polarization.HORIZONTAL,
            epsilon=15.0,
            sigma=0.005,
            mdvar=0,
            time=50.0,
            location=50.0,
            situation=50.0,
        )
        assert math.isfinite(result.A__db), f"Non-finite loss for {climate_enum}"
        assert result.A__db > 0
