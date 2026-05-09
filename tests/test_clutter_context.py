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
    assert ctx.percentile == 50.0
    assert ctx.street_width_m == 27.0
    assert ctx.bel_enabled is False
    assert ctx.bel_building_type == "traditional"
    assert ctx.bel_elevation_angle_deg == 0.0


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


def test_advanced_with_bel_params():
    ctx = ClutterLossContext(
        frequency_mhz=3500.0, distance_m=1000.0,
        tx_height_m=25.0, rx_height_m=2.0,
        model="advanced", percentile=90.0,
        street_width_m=20.0, bel_enabled=True,
        bel_building_type="thermally_efficient",
        bel_elevation_angle_deg=15.0,
    )
    assert ctx.percentile == 90.0
    assert ctx.street_width_m == 20.0
    assert ctx.bel_enabled is True
    assert ctx.bel_building_type == "thermally_efficient"
    assert ctx.bel_elevation_angle_deg == 15.0