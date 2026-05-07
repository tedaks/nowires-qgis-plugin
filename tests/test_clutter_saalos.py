import pytest
from clutter_constants import MAX_CLUTTER_LOSS
from clutter_saalos import clutter_loss_saalos


@pytest.mark.parametrize("d,cch,h_tx,h_rx,h_gnd,pol,f", [
    (1000.0, 0.0, 10.0, 2.0, 0.0, 0, 1000.0),
    (0.0, 15.0, 10.0, 2.0, 0.0, 0, 1000.0),
    (1000.0, 10.0, 30.0, 15.0, 0.0, 0, 1000.0),
    (1000.0, 15.0, 30.0, 15.0, 0.0, 0, 1000.0),
])
def test_boundary_returns_zero(d, cch, h_tx, h_rx, h_gnd, pol, f):
    if h_rx >= cch:
        assert clutter_loss_saalos(d, cch, h_tx, h_rx, h_gnd, pol, f) == 0.0
    else:
        assert clutter_loss_saalos(d, cch, h_tx, h_rx, h_gnd, pol, f) == 0.0


@pytest.mark.parametrize("d,expected", [
    (100.0, 4.888360),
    (150.0, 7.079108),
    (200.0, 9.301259),
])
def test_distance_reference_values_h_pol(d, expected):
    actual = clutter_loss_saalos(d, 15.0, 30.0, 2.0, 0.0, 0, 1000.0)
    assert actual == pytest.approx(expected, abs=1e-3)


@pytest.mark.parametrize("h_rx,expected", [
    (0.0, 13.497084),
    (2.0, 9.301259),
    (5.0, 5.983496),
    (10.0, 3.110594),
    (14.9, 0.025907),
])
def test_rx_height_reference_values(h_rx, expected):
    actual = clutter_loss_saalos(200.0, 15.0, 30.0, h_rx, 0.0, 0, 1000.0)
    assert actual == pytest.approx(expected, abs=1e-3)


def test_loss_is_monotone_non_increasing_in_rx_height():
    prev = float("inf")
    for h_rx in [0.0, 1.0, 2.0, 3.0, 5.0, 8.0, 10.0, 12.0, 14.0, 14.9]:
        v = clutter_loss_saalos(200.0, 15.0, 30.0, h_rx, 0.0, 0, 1000.0)
        assert v <= prev + 1e-9, f"non-monotone at h_rx={h_rx}: {v} > {prev}"
        prev = v


def test_long_distance_caps_at_max():
    v = clutter_loss_saalos(100000.0, 15.0, 30.0, 2.0, 0.0, 0, 1000.0)
    assert v == MAX_CLUTTER_LOSS


def test_frequency_changes_loss():
    f300 = clutter_loss_saalos(200.0, 15.0, 30.0, 2.0, 0.0, 0, 300.0)
    f1000 = clutter_loss_saalos(200.0, 15.0, 30.0, 2.0, 0.0, 0, 1000.0)
    f3000 = clutter_loss_saalos(200.0, 15.0, 30.0, 2.0, 0.0, 0, 3000.0)
    assert f300 == pytest.approx(9.336117, abs=1e-3)
    assert f1000 == pytest.approx(9.301259, abs=1e-3)
    assert f3000 == pytest.approx(9.269451, abs=1e-3)


def test_polarization_accepted_for_all_codes():
    for pol in (0, 1, 2):
        v = clutter_loss_saalos(200.0, 15.0, 30.0, 2.0, 0.0, pol, 1000.0)
        assert 0.0 <= v <= MAX_CLUTTER_LOSS


def test_negative_arte_clamped_to_zero():
    v = clutter_loss_saalos(1.0, 0.5, 0.1, 0.001, 1000.0, 0, 10.0)
    assert v >= 0.0