# -*- coding: utf-8 -*-
"""Unit tests for antenna.py — antenna radiation pattern model."""

import math

from antenna import antenna_gain_factor


class TestAntennaGainFactor:
    """Tests for antenna_gain_factor()."""

    def test_omni_returns_zero(self):
        """Omni antenna (az_deg=None) should return 0 dB gain adjustment."""
        assert antenna_gain_factor(90.0, None, 360.0) == 0.0
        assert antenna_gain_factor(0.0, None, 90.0) == 0.0
        assert antenna_gain_factor(180.0, None, 120.0) == 0.0

    def test_on_boresight(self):
        """On boresight (bearing == azimuth) should return 0 dB."""
        assert antenna_gain_factor(45.0, 45.0, 90.0) == 0.0
        assert antenna_gain_factor(0.0, 0.0, 60.0) == 0.0
        assert antenna_gain_factor(360.0, 0.0, 90.0) == pytest.approx(0.0, abs=1e-10)

    def test_at_beamwidth_edge(self):
        """At beamwidth edge (±beamwidth/2) should return -3 dB."""
        bw = 90.0
        az = 0.0
        # +beamwidth/2
        result = antenna_gain_factor(45.0, az, bw)
        assert result == pytest.approx(-3.0, abs=0.01)
        # -beamwidth/2
        result = antenna_gain_factor(315.0, az, bw)
        assert result == pytest.approx(-3.0, abs=0.01)

    def test_outside_beam(self):
        """Outside beam should return -front_back_db (default 25 dB)."""
        result = antenna_gain_factor(180.0, 0.0, 60.0)
        assert result == -25.0

    def test_custom_front_back(self):
        """Custom front-back ratio."""
        result = antenna_gain_factor(180.0, 0.0, 60.0, front_back_db=20.0)
        assert result == -20.0

    def test_narrow_beam(self):
        """Narrow beam (360 deg bearing away) should be severely attenuated."""
        result = antenna_gain_factor(180.0, 0.0, 10.0)
        assert result == -25.0  # Outside beam

    def test_parabolic_falloff(self):
        """Gain should follow parabolic pattern: attn = 3 * (diff / half_bw)^2."""
        az = 0.0
        bw = 120.0
        half = bw / 2.0
        # At exactly half the way to beam edge (bearing = 30 deg)
        result = antenna_gain_factor(30.0, az, bw)
        expected = -3.0 * (30.0 / 60.0) ** 2  # = -0.75
        assert result == pytest.approx(expected, abs=0.001)


import pytest

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
