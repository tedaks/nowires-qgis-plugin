# -*- coding: utf-8 -*-
# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software under GPLv3 or later. See LICENSE.
"""Regression tests for setup_proxy_opener scoping (v1.5.7).

Two bugs fixed here:
  (a) HTTPPasswordMgrWithDefaultRealm.add_password() was called with
      ``realm=None``, which makes the registered credentials a default-realm
      fallback for any Basic-Auth challenge. The fix passes the proxy realm
      URL so the credentials are scoped.
  (b) proxy_base_url hardcoded ``http://`` regardless of the configured proxy
      scheme; an HTTPS proxy was silently downgraded to HTTP. The fix derives
      the scheme from the realm URL.
"""

import urllib.request
from unittest.mock import MagicMock, patch


def _find_proxy_handler(opener):
    """Return the ProxyHandler instance stored on the OpenerDirector."""
    for h in opener.handlers:
        if isinstance(h, urllib.request.ProxyHandler):
            return h
    raise AssertionError(
        "No ProxyHandler on opener; handlers={}".format([type(h).__name__ for h in opener.handlers])
    )


def _fake_auth_manager(realm_url, username="user", password="secret"):
    """Return a MagicMock for QgsApplication.authManager() whose
    loadAuthenticationConfig populates the auth config with our test data."""
    auth_info = {
        "realm": realm_url,
        "username": username,
        "password": password,
    }

    def load(_auth_id, auth_cfg, _full):
        auth_cfg.configMap = MagicMock(return_value=auth_info)
        return True

    mgr = MagicMock()
    mgr.loadAuthenticationConfig.side_effect = load
    return mgr


class TestProxyAuthRealmScoping:
    def test_add_password_realm_is_not_none(self):
        """Regression: realm must be scoped, not the default-realm wildcard."""
        from NoWires import contour_pipeline

        with patch.object(
            contour_pipeline, "QgsApplication"
        ) as MockApp, patch(
            "urllib.request.HTTPPasswordMgrWithDefaultRealm"
        ) as MgrCls:
            MockApp.authManager.return_value = _fake_auth_manager(
                "http://proxy.example.net:8080"
            )
            mgr_inst = MgrCls.return_value
            opener = contour_pipeline.setup_proxy_opener("auth-id", MagicMock())

        assert opener is not None, "expected a built opener; got None"
        assert mgr_inst.add_password.called
        realm_arg = mgr_inst.add_password.call_args.args[0]
        assert realm_arg is not None, (
            "add_password(realm=None, ...) makes creds a default-realm "
            "fallback; v1.5.7 fix requires a scoped realm"
        )


class TestProxyAuthSchemePreserved:
    def test_https_proxy_not_downgraded(self):
        """Regression: HTTPS proxy realm must not be coerced to http://."""
        from NoWires import contour_pipeline

        with patch.object(contour_pipeline, "QgsApplication") as MockApp:
            MockApp.authManager.return_value = _fake_auth_manager(
                "https://proxy.example.net:8443"
            )
            opener = contour_pipeline.setup_proxy_opener("auth-id", MagicMock())

        assert opener is not None
        proxies = _find_proxy_handler(opener).proxies
        for key in ("http", "https"):
            assert proxies[key].startswith("https://"), (
                "proxy scheme for {!r} hardcoded instead of derived from realm: "
                "{!r}".format(key, proxies[key])
            )

    def test_http_proxy_preserved(self):
        """Sanity: HTTP proxy realm stays http://."""
        from NoWires import contour_pipeline

        with patch.object(contour_pipeline, "QgsApplication") as MockApp:
            MockApp.authManager.return_value = _fake_auth_manager(
                "http://proxy.example.net:3128"
            )
            opener = contour_pipeline.setup_proxy_opener("auth-id", MagicMock())

        assert opener is not None
        proxies = _find_proxy_handler(opener).proxies
        assert proxies["http"].startswith("http://")
        assert proxies["https"].startswith("http://")
