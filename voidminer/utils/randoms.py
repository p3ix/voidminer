from __future__ import annotations

import secrets


def build_canary(prefix: str = "voidminer") -> str:
    return f"{prefix}_{secrets.token_hex(4)}"
