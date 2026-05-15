# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
/***************************************************************************
 NoWires
                     A QGIS plugin
 Radio propagation analysis and terrain tools using ITM with Copernicus GLO-30 DEM
                             -------------------
        begin                : 2026-04-22
        copyright            : (C) 2026 Bortre Tenamo <tedaks@gmail.com>
        email                : tedaks@gmail.com
 ***************************************************************************/

/***************************************************************************
  *                                                                         *
  *   This program is free software; you can redistribute it and/or modify  *
  *   it under the terms of the GNU General Public License as published by  *
  *   the Free Software Foundation; either version 3 of the License, or     *
  *   (at your option) any later version.                                   *
  *                                                                         *
  ***************************************************************************/
"""

from __future__ import annotations

import atexit
import multiprocessing
import multiprocessing.shared_memory

import uuid

import numpy as np


class SharedDEMGrid:
    """Encapsulates the parent-side shared-memory lifecycle for a DEM grid.

    Creates a shared-memory segment, copies the grid data into it, and
    provides cleanup via ``release()`` or the context-manager protocol.
    An atexit safety-net is registered to prevent leaked segments if the
    process exits before ``release()`` is called.
    """

    def __init__(self, grid_data: np.ndarray) -> None:
        self._shm: multiprocessing.shared_memory.SharedMemory | None = None
        self._name: str | None = None
        self._unlinked = False
        self._create(grid_data)

    def _create(self, grid_data: np.ndarray) -> None:
        name = "nowires_dem_" + uuid.uuid4().hex[:20]
        shm = multiprocessing.shared_memory.SharedMemory(
            create=True,
            name=name,
            size=grid_data.nbytes,
        )
        try:
            shared_arr: np.ndarray = np.ndarray(grid_data.shape, dtype=grid_data.dtype, buffer=shm.buf)
            shared_arr[:] = grid_data[:]
        except Exception:
            try:
                shm.close()
                shm.unlink()
            except Exception:
                pass
            raise
        self._shm = shm
        self._name = name
        atexit.register(self._atexit_cleanup)

    @property
    def shm(self):
        return self._shm

    @property
    def name(self):
        return self._name

    def release(self):
        """Close and unlink the shared-memory segment."""
        atexit.unregister(self._atexit_cleanup)
        if self._shm is not None and not self._unlinked:
            try:
                self._shm.close()
            except Exception:
                pass
            try:
                if not self._unlinked:
                    self._shm.unlink()
                    self._unlinked = True
            except Exception:
                pass
            self._shm = None
            self._name = None

    def _atexit_cleanup(self):
        if self._shm is not None and not self._unlinked:
            try:
                self._shm.close()
                self._shm.unlink()
                self._unlinked = True
            except Exception:
                pass
            self._shm = None
            self._name = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False