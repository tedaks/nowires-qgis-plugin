# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
from clutter_constants import MAX_CLUTTER_LOSS


def test_max_clutter_loss_matches_saalos_cap():
    assert MAX_CLUTTER_LOSS == 22.0