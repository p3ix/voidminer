from voidminer.sources.wordlist_builder import (
    list_wordlist_profiles,
    normalize_wordlist_entries,
    prioritize_wordlist,
    resolve_wordlist_profile_paths,
)


def test_wordlist_normalize_and_deduplicate() -> None:
    values = [" Debug ", "debug", "#comment", "", "TOKEN", "token"]
    normalized = normalize_wordlist_entries(values)
    assert normalized == ["debug", "token"]


def test_wordlist_prioritize_keeps_all_items() -> None:
    values = ["tenant_id", "debug_mode", "cache_key", "redirect_url"]
    ordered = prioritize_wordlist(values)
    assert sorted(ordered) == sorted(values)
    assert ordered[0] in {"debug_mode", "cache_key", "redirect_url"}


def test_wordlist_profiles_resolve_existing_files() -> None:
    profiles = list_wordlist_profiles()
    assert "mixed_recon" in profiles
    paths = resolve_wordlist_profile_paths("mixed_recon")
    assert paths
    assert all(path.exists() for path in paths)
