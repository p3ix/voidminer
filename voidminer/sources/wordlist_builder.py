from __future__ import annotations

from pathlib import Path


FAMILY_HINTS: dict[str, tuple[str, ...]] = {
    "debug": ("debug", "trace", "log", "error", "stack", "inspect"),
    "auth": ("token", "auth", "session", "csrf", "nonce", "jwt", "role", "scope"),
    "cache": ("cache", "etag", "purge", "invalidate", "stale", "cdn"),
    "redirect": ("redirect", "return", "next", "callback", "url", "uri", "dest", "target"),
    "assignment": ("admin", "role", "permission", "staff", "superuser", "plan", "billing"),
}

WORDLIST_PROFILE_FILES: dict[str, tuple[str, ...]] = {
    "base": ("params_base.txt",),
    "mega": (
        "params_base.txt",
        "params_debug.txt",
        "params_redirect_ssrf.txt",
        "params_mass_assignment.txt",
        "params_lfi_rce.txt",
        "params_cache_cdn.txt",
        "params_auth_session.txt",
        "params_search_filter.txt",
    ),
    "cache": ("params_cache_cdn.txt",),
    "auth": ("params_auth_session.txt", "params_mass_assignment.txt"),
    "redirect": ("params_redirect_ssrf.txt",),
    "debug": ("params_debug.txt",),
    "mass_assignment": ("params_mass_assignment.txt",),
    "mixed_recon": ("params_base.txt", "params_redirect_ssrf.txt", "params_auth_session.txt", "params_cache_cdn.txt"),
}


def normalize_wordlist_entries(values: list[str]) -> list[str]:
    unique: dict[str, None] = {}
    for raw in values:
        value = raw.strip().lower()
        if not value or value.startswith("#"):
            continue
        if value not in unique:
            unique[value] = None
    return list(unique.keys())


def load_wordlist_file(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return normalize_wordlist_entries(lines)


def load_wordlists(paths: list[Path]) -> list[str]:
    merged: list[str] = []
    for path in paths:
        merged.extend(load_wordlist_file(path))
    return normalize_wordlist_entries(merged)


def list_wordlist_profiles() -> list[str]:
    return sorted(WORDLIST_PROFILE_FILES.keys())


def resolve_wordlist_profile_paths(profile: str) -> list[Path]:
    if profile not in WORDLIST_PROFILE_FILES:
        raise ValueError(f"Unknown wordlist profile: {profile}")
    data_dir = Path(__file__).resolve().parents[2] / "data"
    return [data_dir / filename for filename in WORDLIST_PROFILE_FILES[profile]]


def prioritize_wordlist(values: list[str]) -> list[str]:
    scored: list[tuple[int, str]] = []
    for item in values:
        score = 99
        for idx, (_family, hints) in enumerate(FAMILY_HINTS.items()):
            if any(h in item for h in hints):
                score = idx
                break
        scored.append((score, item))
    scored.sort(key=lambda x: (x[0], x[1]))
    return [item for _score, item in scored]
