from clutter_context import ClutterLossContext


def test_defaults_to_simple_model():
    ctx = ClutterLossContext(
        frequency_mhz=900.0, distance_m=1000.0,
        tx_height_m=30.0, rx_height_m=2.0,
    )
    assert ctx.model == "simple"
    assert ctx.rx_ground_elevation_m == 0.0
    assert ctx.polarization == 0
    assert ctx.cch_override_m is None


def test_advanced_with_overrides():
    ctx = ClutterLossContext(
        frequency_mhz=1800.0, distance_m=2500.0,
        tx_height_m=25.0, rx_height_m=1.5,
        rx_ground_elevation_m=112.0, polarization=1,
        cch_override_m=18.0, model="advanced",
    )
    assert ctx.model == "advanced"
    assert ctx.cch_override_m == 18.0
    assert ctx.polarization == 1