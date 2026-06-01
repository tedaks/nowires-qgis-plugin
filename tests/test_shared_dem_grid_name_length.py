# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
"""Regression test for macOS POSIX shared-memory name-length limit.

macOS XNU defines ``PSHMNAMLEN = 31`` (the max length of a POSIX shm name
INCLUDING the leading slash that ``SharedMemory`` prepends on POSIX).
A name >= 31 chars total fails with ``OSError: [Errno 63] File name too
long``. Linux's ``NAME_MAX`` is 255, which hid this for years.
"""

import re

from NoWires import shared_dem_grid


_MACOS_PSHMNAMLEN = 31  # max chars including leading slash


_MAX_LINUX_PID_DIGITS = 7  # /proc/sys/kernel/pid_max defaults to 4194304


def test_shared_dem_grid_name_fits_macos_limit():
    """The literal name template in shared_dem_grid must fit macOS PSHMNAMLEN.

    Template since v1.5.7: ``nowires_dem_<pid>_<hex_N>``. Worst-case PID is
    7 digits on Linux (pid_max=4194304); macOS PIDs are smaller. The total
    is computed as: leading '/' + prefix + max PID digits + '_' + hex suffix.
    """
    src = open(shared_dem_grid.__file__).read()
    m = re.search(
        r'name\s*=\s*"(nowires_dem_)\{\}_\{\}"\.format\(os\.getpid\(\),\s*uuid\.uuid4\(\)\.hex\[:(\d+)\]\)',
        src,
    )
    assert m is not None, "could not locate name template in shared_dem_grid.py"
    prefix_len = len(m.group(1))
    suffix_len = int(m.group(2))
    total_with_slash = 1 + prefix_len + _MAX_LINUX_PID_DIGITS + 1 + suffix_len
    assert total_with_slash <= _MACOS_PSHMNAMLEN, (
        "shm name '/{prefix}<{pid_digits}-digit pid>_<{hex_len} hex>' is "
        "{total} chars worst-case; macOS limit is {limit}. "
        "Truncate the hex suffix or the prefix.".format(
            prefix=m.group(1), pid_digits=_MAX_LINUX_PID_DIGITS,
            hex_len=suffix_len, total=total_with_slash,
            limit=_MACOS_PSHMNAMLEN,
        )
    )
