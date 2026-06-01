# Copyright (C) 2026 Bortre Tenamo <tedaks@gmail.com>
# SPDX-License-Identifier: MIT
import math

_FORMULA_TRIGGER_CHARS = frozenset({'=', '+', '@', '\N{EN DASH}', '\N{MINUS SIGN}'})
_UNICODE_WHITESPACE = "\t\r\u3000\u2003\u2002\ufeff"


def csv_safe(value):
    s = str(value)
    s = s.replace("\r", " ").replace("\n", " ")
    stripped = s.lstrip(_UNICODE_WHITESPACE + " ")
    if stripped and stripped[0] in _FORMULA_TRIGGER_CHARS:
        return "'" + s
    if stripped.startswith("-") and len(stripped) > 1:
        try:
            float(stripped)
        except ValueError:
            return "'" + s
    return s


def sanitize_json(obj):
    if isinstance(obj, dict):
        return {k: sanitize_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize_json(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj
