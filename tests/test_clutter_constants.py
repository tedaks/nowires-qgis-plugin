from clutter_constants import MAX_CLUTTER_LOSS


def test_max_clutter_loss_matches_saalos_cap():
    assert MAX_CLUTTER_LOSS == 22.0