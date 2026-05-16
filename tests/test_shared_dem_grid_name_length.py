# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression test for macOS POSIX shared-memory name-length limit.

macOS XNU defines ``PSHMNAMLEN = 31`` (the max length of a POSIX shm name
INCLUDING the leading slash that ``SharedMemory`` prepends on POSIX).
A name >= 31 chars total fails with ``OSError: [Errno 63] File name too
long``. Linux's ``NAME_MAX`` is 255, which hid this for years.
"""

import re

from NoWires import shared_dem_grid


_MACOS_PSHMNAMLEN = 31  # max chars including leading slash


def test_shared_dem_grid_name_fits_macos_limit():
    """The literal name template in shared_dem_grid must be <= 30 chars."""
    src = open(shared_dem_grid.__file__).read()
    # Find the name = "nowires_dem_" + uuid.uuid4().hex[:N] expression.
    m = re.search(r'name\s*=\s*"(nowires_dem_)"\s*\+\s*uuid\.uuid4\(\)\.hex\[:(\d+)\]', src)
    assert m is not None, "could not locate name template in shared_dem_grid.py"
    prefix_len = len(m.group(1))
    suffix_len = int(m.group(2))
    total_with_slash = 1 + prefix_len + suffix_len
    assert total_with_slash <= _MACOS_PSHMNAMLEN, (
        "shm name '/{prefix}<{hex_len} hex>' is {total} chars; macOS limit is {limit}. "
        "Truncate the hex suffix.".format(
            prefix=m.group(1), hex_len=suffix_len,
            total=total_with_slash, limit=_MACOS_PSHMNAMLEN,
        )
    )
