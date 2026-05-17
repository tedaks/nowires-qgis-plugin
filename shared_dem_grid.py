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
import glob
import multiprocessing
import multiprocessing.shared_memory
import os
import re
import uuid
import weakref

import numpy as np


_SHM_NAME_RE = re.compile(r"^nowires_dem_(\d+)_[0-9a-f]+$")

_pending_releases: dict = {}  # id(obj) -> SharedDEMGrid weak reference
_atexit_registered = False


def _atexit_release_pending():
    """Module-level atexit: release any shared-memory segments still alive."""
    for obj_id in list(_pending_releases):
        ref = _pending_releases.get(obj_id)
        if ref is not None:
            obj = ref()
            if obj is not None:
                obj.release()


def cleanup_stale_shm_entries(dev_shm_dir: str, my_uid: int) -> None:
    """Remove ``/dev/shm/nowires_dem_<pid>_<hex>`` entries that are stale AND
    belong to the calling user.

    Stale means: the embedded PID no longer maps to a live process. Per-user
    scoping means: ``stat.st_uid`` must equal ``my_uid``. Both conditions
    must hold; on a shared workstation, this prevents one user's QGIS
    startup from destroying another user's in-flight DEM segments. Entries
    whose name does not match the v1.5.7 template are left untouched.
    """
    if not os.path.isdir(dev_shm_dir):
        return
    for entry in glob.iglob(os.path.join(dev_shm_dir, "nowires_dem_*")):
        m = _SHM_NAME_RE.match(os.path.basename(entry))
        if m is None:
            continue
        try:
            st = os.stat(entry)
        except OSError:
            continue
        if st.st_uid != my_uid:
            continue
        pid = int(m.group(1))
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            pass  # PID is gone; safe to unlink
        except PermissionError:
            continue  # PID exists under a different uid; do not unlink
        except OSError:
            continue
        else:
            continue  # signal succeeded -> process is alive
        try:
            os.unlink(entry)
        except OSError:
            pass


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
        # macOS limits POSIX shm names to 31 chars total (including the leading
        # '/' that SharedMemory prepends). Template: nowires_dem_<pid>_<hex9>.
        # Linux max PID is 7 digits (4194304); 12 + 7 + 1 + 9 = 29, plus '/'
        # = 30 — comfortably under XNU's PSHMNAMLEN=31. macOS PIDs are
        # smaller still. Embedding the creator PID lets cleanup on shared
        # workstations distinguish stale entries from other users' live
        # segments (see NoWiresPlugin._cleanup_stale_shared_memory).
        name = "nowires_dem_{}_{}".format(os.getpid(), uuid.uuid4().hex[:9])
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
        _pending_releases[id(self)] = weakref.ref(self)
        global _atexit_registered
        if not _atexit_registered:
            atexit.register(_atexit_release_pending)
            _atexit_registered = True

    @property
    def shm(self):
        return self._shm

    @property
    def name(self):
        return self._name

    def release(self):
        """Close and unlink the shared-memory segment."""
        _pending_releases.pop(id(self), None)
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
        _pending_releases.pop(id(self), None)
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

    def __del__(self):
        if self._shm is not None and not self._unlinked:
            self.release()