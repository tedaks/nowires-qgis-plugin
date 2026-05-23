# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
import threading
import numpy as np
from NoWires.shared_dem_grid import SharedDEMGrid


def test_concurrent_create_release_no_corruption():
    errors = []
    barrier = threading.Barrier(20)

    def worker(_i):
        try:
            barrier.wait()
            grid = SharedDEMGrid(np.zeros((2, 2), dtype=np.float32))
            assert grid is not None
            grid.release()
        except Exception as e:
            errors.append((_i, e))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    assert not errors, f"Concurrent errors: {errors}"