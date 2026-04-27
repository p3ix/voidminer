from __future__ import annotations

import secrets


def build_canary(prefix: str = "voidminer") -> str:
    return f"{prefix}_{secrets.token_hex(4)}"


def build_payload_candidates(profile: str, canary: str) -> list[str]:
    base = [canary, "true", "1", "on", "debug", "verbose", "0", "999", ""]
    if profile == "fast":
        return [canary, "1", "debug"]
    if profile == "balanced":
        return [canary, "true", "1", "debug", "verbose", ""]
    # deep
    return base
