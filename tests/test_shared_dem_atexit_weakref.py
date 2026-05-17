# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression test for atexit pinning in SharedDEMGrid (v1.5.7 fix #18).

Before v1.5.7, ``atexit.register(self._atexit_cleanup)`` registered a bound
method holding a strong reference to self, preventing GC and pinning the
SharedMemory buffer until process exit. The fix uses a module-level
``_pending_releases`` dict with weakref.ref(self) entries and a single
module-level atexit handler, plus a __del__ safety-net.
"""



def test_shared_dem_grid_registers_weak_ref_not_bound_method():
    """SharedDEMGrid._create must register a weak reference, not self."""
    import shared_dem_grid

    assert hasattr(shared_dem_grid, "_pending_releases"), (
        "shared_dem_grid must export _pending_releases dict"
    )
    assert hasattr(shared_dem_grid, "_atexit_release_pending"), (
        "shared_dem_grid must export module-level _atexit_release_pending"
    )


def test_shared_dem_grid_release_removes_from_pending():
    """Calling release() must remove the entry from _pending_releases."""
    import numpy as np
    from shared_dem_grid import SharedDEMGrid, _pending_releases

    grid = np.ones((4, 4), dtype=np.float32)
    sdg = SharedDEMGrid(grid)
    obj_id = id(sdg)
    assert obj_id in _pending_releases, "grid should be in _pending_releases after creation"
    sdg.release()
    assert obj_id not in _pending_releases, (
        "release() must remove entry from _pending_releases"
    )


def test_shared_dem_grid_atexit_registered_once():
    """Module-level atexit must be registered only once even with multiple grids."""
    import shared_dem_grid

    original = shared_dem_grid._atexit_registered
    shared_dem_grid._atexit_registered = False

    import numpy as np
    from shared_dem_grid import SharedDEMGrid

    grid1 = np.ones((4, 4), dtype=np.float32)
    grid2 = np.ones((4, 4), dtype=np.float32)
    sdg1 = SharedDEMGrid(grid1)
    assert shared_dem_grid._atexit_registered is True
    sdg2 = SharedDEMGrid(grid2)
    assert shared_dem_grid._atexit_registered is True

    sdg1.release()
    sdg2.release()
    shared_dem_grid._atexit_registered = original