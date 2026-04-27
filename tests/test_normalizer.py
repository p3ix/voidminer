from voidminer.core.normalizer import normalize_text


def test_normalize_dynamic_noise() -> None:
    raw = "request_id=abc12345 2026-04-27T10:20:30Z uuid 123e4567-e89b-12d3-a456-426614174000 999999999999"
    normalized = normalize_text(raw)
    assert "<iso_ts>" in normalized
    assert "<uuid>" in normalized
    assert "<large_num>" in normalized
