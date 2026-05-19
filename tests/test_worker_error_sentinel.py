# SPDX-License-Identifier: GPL-3.0-or-later
from coverage._result_dispatch import WorkerError, apply_batch_results
import numpy as np


def test_worker_error_is_dataclass():
    we = WorkerError("boom")
    assert we.message == "boom"
    assert "WorkerError" in repr(we) and "boom" in repr(we)


def test_worker_error_frozen():
    we = WorkerError("boom")
    try:
        we.message = "changed"
        assert False, "Should be frozen"
    except AttributeError:
        pass


def test_apply_batch_results_with_worker_error():
    loss_grid = np.full((2, 2), -999.0)
    prx_grid = np.full((2, 2), -999.0)
    itm_loss_grid = np.full((2, 2), -999.0)
    clutter_loss_grid = np.full((2, 2), -999.0)
    clutter_rx_db_grid = np.full((2, 2), -999.0)
    bel_rx_db_grid = np.full((2, 2), -999.0)
    we = WorkerError("some error")
    results = [None, we, (0, 0, -50.0, -80.0, -120.0, 5.0, 3.0, 0.0)]
    pixels_failed = apply_batch_results(
        results, loss_grid, prx_grid, itm_loss_grid,
        clutter_loss_grid, clutter_rx_db_grid, bel_rx_db_grid,
    )
    assert pixels_failed == 2
    assert loss_grid[0, 0] == -50.0
    assert prx_grid[0, 0] == -80.0


def test_apply_batch_results_all_normal():
    loss_grid = np.full((1, 1), -999.0)
    prx_grid = np.full((1, 1), -999.0)
    itm_loss_grid = np.full((1, 1), -999.0)
    clutter_loss_grid = np.full((1, 1), -999.0)
    clutter_rx_db_grid = np.full((1, 1), -999.0)
    bel_rx_db_grid = np.full((1, 1), -999.0)
    results = [(0, 0, -60.0, -90.0, -130.0, 4.0, 2.0, 0.5)]
    pixels_failed = apply_batch_results(
        results, loss_grid, prx_grid, itm_loss_grid,
        clutter_loss_grid, clutter_rx_db_grid, bel_rx_db_grid,
    )
    assert pixels_failed == 0
    assert loss_grid[0, 0] == -60.0